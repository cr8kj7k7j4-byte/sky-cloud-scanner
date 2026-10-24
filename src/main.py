from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import json

from .config import (
    TOP_N, DEEP_DIVE_N, STRICT_OFFICIAL_MODE, ALLOW_MIS_OTC_FALLBACK,
    ACCOUNT_EQUITY, RISK_PER_TRADE_PCT, DAILY_LOSS_LIMIT_PCT,
    MAX_PORTFOLIO_HEAT_PCT, MAX_POSITION_PCT, CORRELATION_LIMIT_PCT,
    MAX_CONCURRENT_POSITIONS, CAUTION_LOSS_STREAK, DEFENSIVE_LOSS_STREAK,
    LOCKDOWN_DRAWDOWN_PCT, LOT_SIZE, DAILY_PNL, OPEN_RISK,
    CONCURRENT_POSITIONS, CORRELATED_OPEN_RISK, ACCOUNT_DRAWDOWN_PCT,
    CONSECUTIVE_LOSSES,
)
from .official import load_official_universe, fetch_mis_quotes
from .fugle import get_ticker, get_quote, get_candles
from .sky_rules import first_gate, score_for_ranking, enrich
from .notifier import send_telegram
from .risk_engine import RiskPolicy, evaluate_candidate, drawdown_state
from .feature_engine import build_features
from .regime_engine import detect_regime
from .ml_layer import baseline_model_predictions, ensemble
from .explainability import explain
from .validation import evaluate_validation_gate
from .evidence_ledger import build_evidence_ledger
from .market_intelligence import summarize_market
from .relative_strength import apply_relative_strength
from .event_risk import assess_event_risk

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output")

RISK_STATUS_ZH = {
    "ALLOW": "允許進場",
    "BLOCK": "禁止進場",
    "RISK_INPUT_REQUIRED": "風控資料不足",
}
RISK_STATE_ZH = {
    "NORMAL": "正常",
    "CAUTION": "警戒",
    "DEFENSIVE": "防守",
    "LOCKDOWN": "鎖定",
}

def _risk_policy():
    return RiskPolicy(
        risk_per_trade_pct=RISK_PER_TRADE_PCT,
        daily_loss_limit_pct=DAILY_LOSS_LIMIT_PCT,
        max_portfolio_heat_pct=MAX_PORTFOLIO_HEAT_PCT,
        max_position_pct=MAX_POSITION_PCT,
        correlation_limit_pct=CORRELATION_LIMIT_PCT,
        max_concurrent_positions=MAX_CONCURRENT_POSITIONS,
        caution_loss_streak=CAUTION_LOSS_STREAK,
        defensive_loss_streak=DEFENSIVE_LOSS_STREAK,
        lockdown_drawdown_pct=LOCKDOWN_DRAWDOWN_PCT,
        lot_size=LOT_SIZE,
    )

def _portfolio_context():
    return {
        "account_equity": ACCOUNT_EQUITY,
        "daily_pnl": DAILY_PNL,
        "open_risk": OPEN_RISK,
        "concurrent_positions": CONCURRENT_POSITIONS,
        "correlated_open_risk": CORRELATED_OPEN_RISK,
        "drawdown_pct": ACCOUNT_DRAWDOWN_PCT,
        "consecutive_losses": CONSECUTIVE_LOSSES,
    }

def run():
    now = datetime.now(TZ)
    OUT.mkdir(exist_ok=True)

    policy = _risk_policy()
    portfolio_context = _portfolio_context()
    portfolio_state = drawdown_state(
        ACCOUNT_DRAWDOWN_PCT, CONSECUTIVE_LOSSES, policy
    )

    st = {
        "run_time": now.isoformat(),
        "version": "0.4",
        "full_market_scan": False,
        "strict_official_mode": STRICT_OFFICIAL_MODE,
        "warnings": [],
        "source_health": {},
        "market_intelligence": {},
        "event_risk": {},
        "top100": [],
        "deep": [],
        "deep_rejected": [],
        "deep_unverified": [],
        "ml_foundation": {
            "enabled": True,
            "mode": "RESEARCH_ONLY",
            "production_eligible": False,
        },
        "risk_engine": {
            "enabled": True,
            "policy": policy.to_dict(),
            "portfolio_context": portfolio_context,
            "state": portfolio_state,
            "state_zh": RISK_STATE_ZH.get(portfolio_state, portfolio_state),
        },
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

        st["market_intelligence"] = summarize_market(working_rows)
        st["event_risk"] = assess_event_risk([])

        # Do not silently replace an incomplete official chain with a
        # plan-restricted Fugle Snapshot endpoint.
        if len(working_rows) < 300:
            st["warnings"].append(
                "盤中有效報價不足 300 檔；本次不以 Fugle Snapshot 補洞，"
                "避免把方案權限或資料缺口誤判為完整市場。"
            )

        working_rows = apply_relative_strength(working_rows)

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
                ks = get_candles(row["symbol"], "5")
                item = enrich(
                    row,
                    get_ticker(row["symbol"]),
                    get_quote(row["symbol"]),
                    ks,
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

                features = build_features(
                    item,
                    ks.get("data", []) if isinstance(ks, dict) else [],
                    market_return_pct=None,
                ).to_dict()
                regime = detect_regime(
                    index_change_pct=None,
                    breadth_pct=None,
                    volatility_pct=features.get("volatility_5"),
                )
                preds = baseline_model_predictions(features, horizon_days=5)
                ml = ensemble(preds, regime.label)
                ml["models"] = [p.to_dict() for p in preds]
                ml["regime"] = regime.to_dict()
                ml["explainability"] = explain(features, ml)
                ml["validation"] = evaluate_validation_gate()
                item["features"] = features
                item["ml"] = ml
                item["market_intelligence"] = st["market_intelligence"]
                item["event_risk"] = st["event_risk"]
                item["evidence_ledger"] = build_evidence_ledger(item, now.isoformat())

                risk = evaluate_candidate(item, portfolio_context, policy)
                risk["status_zh"] = RISK_STATUS_ZH.get(risk["status"], risk["status"])
                risk["state_zh"] = RISK_STATE_ZH.get(risk["state"], risk["state"])
                item["risk"] = risk
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

        lines += [
            "",
            "【P0-M 市場情報】",
            f"市場偏向：{st['market_intelligence'].get('market_bias', 'UNKNOWN')}｜上漲家數比：{st['market_intelligence'].get('breadth_pct')}%",
            f"事件風險：{st['event_risk'].get('level', 'UNKNOWN')}｜動作：{st['event_risk'].get('action', 'VERIFY_BEFORE_TRADE')}",
            "",
            "【P0-R 風控總覽】",
            f"帳戶狀態：{RISK_STATE_ZH.get(portfolio_state, portfolio_state)}",
            (
                f"帳戶資金：{ACCOUNT_EQUITY:,.0f}｜"
                f"單筆風險上限：{RISK_PER_TRADE_PCT*100:.2f}%｜"
                f"單日最大虧損：{DAILY_LOSS_LIMIT_PCT*100:.2f}%｜"
                f"最大持倉風險：{MAX_PORTFOLIO_HEAT_PCT*100:.2f}%"
            ),
            "",
            "【可繼續深查候選】",
        ]
        if not deep:
            lines.append("目前沒有完成且通過基礎否決條件的深查候選；不產生交易建議。")

        for i, x in enumerate(deep[:10], 1):
            flags = "、".join(x.get("flags", [])) or "待確認"
            risk = x.get("risk", {})
            risk_status = risk.get("status_zh", "未檢查")
            risk_state = risk.get("state_zh", "未檢查")
            reasons = "、".join(risk.get("reasons", [])) or "無"
            required = "、".join(risk.get("required_inputs", []))
            risk_line = (
                f"風控：{risk_status}｜帳戶狀態：{risk_state}｜"
                f"建議部位：{risk.get('recommended_shares', 0):,}股"
            )
            if required:
                risk_line += f"｜缺少：{required}"
            lines.append(
                f'{i}. {x["symbol"]} {x.get("name","")} '
                f'{x["last"]:.2f} ({x["change_pct"]:+.2f}%) '
                f'量{x.get("volume",0):,}｜{flags}｜上限:{x.get("classification_cap")}'
            )
            lines.append(f"   {risk_line}")
            ml = x.get("ml", {})
            if ml:
                consensus_zh = {
                    "BULLISH": "偏多",
                    "BEARISH": "偏空",
                    "NEUTRAL": "中性",
                }.get(ml.get("consensus"), ml.get("consensus", "未判定"))
                lines.append(
                    f"   ML研究層：{consensus_zh}｜"
                    f"5日預期報酬：{ml.get('expected_return_pct')}%｜"
                    f"信心：{float(ml.get('confidence') or 0)*100:.1f}%｜"
                    f"市場狀態：{ml.get('regime', {}).get('label', '未判定')}｜"
                    f"資格：研究用"
                )
            if reasons != "無":
                lines.append(f"   原因：{reasons}")

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
            "注意：rank_score 與 relative_strength_score 僅用於候選排序／橫向比較，不是勝率、SSS 或 EES。",
            "Evidence Ledger 規則：可觀察事實與 Sky 衍生推論分開記錄；缺乏事件資料時 Event Risk 一律為 UNKNOWN，不得視為無風險。",
            "P0-R 規則：任何 AI／策略訊號都不得繞過風控；缺少停損、目標價或帳戶資金時，風控一律標示「資料不足」，不得視為可進場。",
            "P0-ML 規則：目前僅為研究用 baseline；未通過 Walk-forward／OOS／成本壓力／資料洩漏檢查／Paper Trading 前，不得提升為正式交易依據。",
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
