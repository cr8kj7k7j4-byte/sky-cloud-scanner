from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import json

from .config import TOP_N, DEEP_DIVE_N, STRICT_OFFICIAL_MODE, ALLOW_MIS_OTC_FALLBACK
from .official import load_official_universe, fetch_mis_quotes
from .fugle import get_ticker, get_quote, get_candles
from .sky_rules import first_gate, score_for_ranking, enrich
from .notifier import send_telegram

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output")

def run():
    now = datetime.now(TZ)
    OUT.mkdir(exist_ok=True)

    st = {
        "run_time": now.isoformat(),
        "version": "0.4",
        "full_market_scan": False,
        "strict_official_mode": STRICT_OFFICIAL_MODE,
        "warnings": [],
        "source_health": {},
        "top100": [],
        "deep": [],
        "deep_rejected": [],
        "deep_unverified": [],
    }

    try:
        universe, ust = load_official_universe()
        st["source_health"]["official_universe"] = ust
        st["universe_count"] = len(universe)

        rows, miswarn = fetch_mis_quotes(universe)
        st["warnings"].extend(miswarn)
        st["mis_quote_count"] = len(rows)

        twse_rows = [x for x in rows if x["exchange"] == "TWSE"]
        otc_rows = [x for x in rows if x["exchange"] == "TPEx"]

        official_universe_ok = ust["twse"] >= 500 and ust["tpex"] >= 400
        twse_intraday_ok = len(twse_rows) >= 400

        # Free/public TPEx official full-market real-time feed is not certified
        # in this build. MIS OTC can be used operationally but cannot promote
        # strict full-market status.
        tpex_official_intraday_ok = False

        st["source_health"]["twse_intraday"] = {
            "ok": twse_intraday_ok,
            "source": "TWSE MIS",
            "count": len(twse_rows),
        }
        st["source_health"]["tpex_intraday"] = {
            "ok": False,
            "source": (
                "TPEx official public/free full-market real-time feed "
                "not certified; TWSE MIS OTC is operational fallback only"
            ),
            "fallback_count": len(otc_rows),
        }

        if STRICT_OFFICIAL_MODE:
            st["full_market_scan"] = bool(
                official_universe_ok
                and twse_intraday_ok
                and tpex_official_intraday_ok
            )
            if not st["full_market_scan"]:
                st["warnings"].append(
                    "未完成全市場掃描：TPEx 官方免費公開來源未能驗證完整盤中"
                    "全市場即時資料鏈；候選最高只列 A。"
                )
        else:
            st["full_market_scan"] = bool(
                official_universe_ok and len(rows) >= 700
            )

        working_rows = rows if ALLOW_MIS_OTC_FALLBACK else twse_rows

        # Do not silently replace an incomplete official chain with a
        # plan-restricted Fugle Snapshot endpoint.
        if len(working_rows) < 300:
            st["warnings"].append(
                "盤中有效報價不足 300 檔；本次不以 Fugle Snapshot 補洞，"
                "避免把方案權限或資料缺口誤判為完整市場。"
            )

        passed = []
        for r in working_rows:
            ok, reasons = first_gate(r)
            r["gate_reasons"] = reasons
            if ok:
                r["rank_score"] = score_for_ranking(r)
                passed.append(r)

        passed.sort(key=lambda x: x["rank_score"], reverse=True)
        top = passed[:TOP_N]
        st["top100"] = top

        # Deep-dive enough rows to fill DEEP_DIVE_N verified, non-rejected
        # candidates. Confirmed limit-up / non-day-tradable names do not consume
        # the effective candidate quota.
        deep = []
        rejected = []
        unverified = []
        probe_limit = min(len(top), max(DEEP_DIVE_N * 4, DEEP_DIVE_N))

        for row in top[:probe_limit]:
            try:
                item = enrich(
                    row,
                    get_ticker(row["symbol"]),
                    get_quote(row["symbol"]),
                    get_candles(row["symbol"], "5"),
                )
                item["classification_cap"] = (
                    "A"
                    if not st["full_market_scan"]
                    else "A+ eligible only after all gates"
                )

                x_flags = [f for f in item.get("flags", []) if str(f).startswith("X:")]
                if x_flags:
                    rejected.append(item)
                    continue

                deep.append(item)
                if len(deep) >= DEEP_DIVE_N:
                    break

            except PermissionError as e:
                item = dict(row)
                item["flags"] = [f"Fugle深查權限不足:{e}"]
                item["classification_cap"] = "A"
                unverified.append(item)

            except Exception as e:
                item = dict(row)
                item["flags"] = [f"Fugle深查失敗:{type(e).__name__}"]
                item["classification_cap"] = "A"
                unverified.append(item)

        st["deep"] = deep
        st["deep_rejected"] = rejected[:20]
        st["deep_unverified"] = unverified[:20]

        lines = [
            f"Sky Cloud Scanner v0.4｜{now:%Y-%m-%d %H:%M}",
            (
                f"官方母池 TWSE {ust['twse']}｜TPEx {ust['tpex']}｜"
                f"MIS有效報價 {len(rows)}｜第一層通過 {len(passed)}"
            ),
        ]

        if st["full_market_scan"]:
            lines.append("✅ 已完成嚴格定義的全市場資料鏈。")
        else:
            lines.append(
                "⚠ 未完成全市場掃描；任何候選最高只列 A，不得宣告 A+。"
            )

        lines.append(
            "來源：TWSE官方母池＋TPEx官方母池；盤中上市=TWSE MIS；"
            "上櫃 MIS 僅為操作備援，非 TPEx 官方完整盤中資料鏈。"
        )

        lines += ["", "【可繼續深查候選】"]
        if not deep:
            lines.append("目前沒有完成且通過基礎否決條件的深查候選；不產生交易建議。")

        for i, x in enumerate(deep[:10], 1):
            flags = "、".join(x.get("flags", [])) or "待確認"
            lines.append(
                f'{i}. {x["symbol"]} {x.get("name","")} '
                f'{x["last"]:.2f} ({x["change_pct"]:+.2f}%) '
                f'量{x.get("volume",0):,}｜{flags}｜上限:{x.get("classification_cap")}'
            )

        if rejected:
            lines += ["", "【已確認淘汰，不占有效深查名額】"]
            for x in rejected[:8]:
                flags = "、".join(x.get("flags", []))
                lines.append(
                    f'{x["symbol"]} {x.get("name","")}｜{flags}'
                )

        if unverified:
            lines += ["", "【資料不足／深查未完成】"]
            for x in unverified[:8]:
                flags = "、".join(x.get("flags", []))
                lines.append(
                    f'{x["symbol"]} {x.get("name","")}｜{flags}'
                )

        lines += [
            "",
            "注意：rank_score 僅用於候選排序，不是勝率、SSS 或 EES。",
            (
                "A+ 必須再通過 Market Gate→Sector/RS→MTF→SSS→Phase→"
                "Anti-Chase→Breakout Quality→Setup+Trigger→"
                "Devil’s Advocate→EES→RR Gate。"
            ),
        ]

        msg = "\n".join(lines)
        (OUT / "latest.txt").write_text(msg, encoding="utf-8")
        (OUT / "latest.json").write_text(
            json.dumps(st, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        send_telegram(msg)

    except Exception as e:
        err = (
            f"Sky Cloud Scanner v0.4 執行失敗｜{now:%Y-%m-%d %H:%M}\n"
            f"{type(e).__name__}: {e}\n不產生交易建議。"
        )
        st["warnings"].append(err)
        (OUT / "latest.txt").write_text(err, encoding="utf-8")
        (OUT / "latest.json").write_text(
            json.dumps(st, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(err)
        raise

if __name__ == "__main__":
    run()
