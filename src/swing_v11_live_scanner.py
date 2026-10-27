from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

from .official import fetch_mis_quotes, load_official_universe
from .sky_mobile_table import render_mobile_table

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output/swing_v11_live")


def _f(v):
    try:
        return float(v)
    except Exception:
        return None


def _mean(xs):
    return statistics.mean(xs) if xs else None


def load_daily_history(history_dir: str) -> dict[str, list[dict]]:
    bysym = {}
    for p in sorted(Path(history_dir).rglob("*_D.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        sym = str(obj.get("symbol") or p.stem.replace("_D", ""))
        rows = obj.get("data") or obj.get("rows") or obj.get("history") or []
        arr = []
        for r in rows:
            ds = str(r.get("date") or r.get("trading_date") or "")[:10]
            op, hi, lo, cl = map(_f, (r.get("open"), r.get("high"), r.get("low"), r.get("close")))
            vol = _f(r.get("volume")) or 0.0
            if ds and None not in (op, hi, lo, cl):
                arr.append({
                    "date": ds,
                    "open": op,
                    "high": hi,
                    "low": lo,
                    "close": cl,
                    "volume": vol,
                })
        arr.sort(key=lambda x: x["date"])
        if arr:
            bysym[sym] = arr
    return bysym


def choose_signal_date(bysym: dict[str, list[dict]]) -> tuple[str | None, dict]:
    counts = Counter()
    for rows in bysym.values():
        counts.update(r["date"] for r in rows)
    if not counts:
        return None, {"date_counts": {}, "max_cross_section": 0}
    max_cross = max(counts.values())
    threshold = max(20, int(max_cross * 0.80))
    eligible_dates = [d for d, n in counts.items() if n >= threshold]
    signal_date = max(eligible_dates) if eligible_dates else max(counts)
    return signal_date, {
        "max_cross_section": max_cross,
        "selected_date_count": counts.get(signal_date, 0),
        "selection_threshold": threshold,
    }


def build_signal_cross_section(bysym: dict[str, list[dict]], signal_date: str):
    raw = []
    for sym, days in bysym.items():
        idx = next((i for i, r in enumerate(days) if r["date"] == signal_date), None)
        if idx is None or idx < 60:
            continue
        closes = [x["close"] for x in days]
        highs = [x["high"] for x in days]
        d = days[idx]
        ma20 = _mean(closes[idx - 19 : idx + 1])
        ma60 = _mean(closes[idx - 59 : idx + 1])
        if not ma20 or not ma60 or closes[idx - 20] == 0:
            continue
        ret20 = closes[idx] / closes[idx - 20] - 1.0
        prior20 = max(highs[idx - 20 : idx])
        range_pct = (d["high"] - d["low"]) / d["close"] if d["close"] else None
        raw.append({
            "symbol": sym,
            "date": signal_date,
            "close": d["close"],
            "signal_low": d["low"],
            "signal_high": d["high"],
            "ma20": ma20,
            "ma60": ma60,
            "ret20": ret20,
            "prior20_high": prior20,
            "range_pct": range_pct,
        })

    if len(raw) < 20:
        return [], None

    breadth = sum(r["close"] > r["ma20"] for r in raw) / len(raw)
    rs_sorted = sorted(r["ret20"] for r in raw)
    for r in raw:
        r["breadth"] = breadth
        r["rs_pct"] = sum(v <= r["ret20"] for v in rs_sorted) / len(rs_sorted)
    return raw, breadth


def frozen_signal_pass(r: dict) -> tuple[bool, list[str]]:
    reasons = []
    if r["breadth"] < 0.50:
        reasons.append("Market Gate breadth<0.50")
    if not (r["close"] > r["ma20"] > r["ma60"]):
        reasons.append("Trend Gate fail")
    if r["rs_pct"] < 0.70:
        reasons.append("RS percentile<0.70")
    if not (r["close"] > r["prior20_high"]):
        reasons.append("20D breakout fail")
    if (r["close"] / r["ma20"] - 1.0) > 0.08:
        reasons.append("Anti-Chase close/MA20>8%")
    if r["range_pct"] is None or r["range_pct"] > 0.08:
        reasons.append("Anti-Chase daily range>8%")
    return not reasons, reasons


def _entry_status(now: datetime) -> tuple[str, str]:
    t = now.time()
    if dtime(9, 0) <= t <= dtime(9, 5):
        return "OPEN_ENTRY_WINDOW", "原凍結規則為 D+1 開盤進場；目前仍在開盤執行窗口。"
    if t > dtime(9, 5):
        return "OPEN_ENTRY_PASSED_NO_CHASE", "原凍結規則的 D+1 開盤進場已過；不得把盤中現價改寫成新 Trigger。"
    return "PREOPEN_WAIT", "尚未進入 D+1 開盤執行時間。"


def run(history_dir: str, top_n: int = 20):
    now = datetime.now(TZ)
    OUT.mkdir(parents=True, exist_ok=True)

    bysym = load_daily_history(history_dir)
    signal_date, date_meta = choose_signal_date(bysym)
    if not signal_date:
        raise RuntimeError("canonical daily history has no usable signal date")

    cross, breadth = build_signal_cross_section(bysym, signal_date)
    frozen_pass = []
    for r in cross:
        ok, reasons = frozen_signal_pass(r)
        if ok:
            frozen_pass.append(r)

    universe, universe_health = load_official_universe()
    quotes, warnings = fetch_mis_quotes(universe)
    quote_by_symbol = {str(x.get("symbol")): x for x in quotes}

    twse_n = sum(x.get("exchange") == "TWSE" for x in quotes)
    tpex_n = sum(x.get("exchange") == "TPEx" for x in quotes)
    coverage = round(len(quotes) / len(universe) * 100.0, 2) if universe else 0.0
    operational_full_market_scan = bool(
        universe
        and universe_health.get("twse", 0) >= 500
        and universe_health.get("tpex", 0) >= 400
        and twse_n >= 400
        and tpex_n >= 300
        and coverage >= 80.0
    )

    status_code, status_text = _entry_status(now)
    candidates = []
    for sig in frozen_pass:
        q = quote_by_symbol.get(sig["symbol"])
        if not q:
            continue
        entry_open = _f(q.get("open"))
        current = _f(q.get("last"))
        if entry_open is None:
            continue
        if entry_open >= 100:
            continue
        stop = sig["signal_low"]
        if stop >= entry_open:
            continue
        risk = entry_open - stop
        target = entry_open + 3.0 * risk

        item = {
            **sig,
            "name": q.get("name"),
            "exchange": q.get("exchange"),
            "entry_date": now.date().isoformat(),
            "entry_open": entry_open,
            "current_price": current,
            "stop": round(stop, 4),
            "target_3r": round(target, 4),
            "gross_rr": 3.0,
            "change_pct": q.get("change_pct"),
            "volume": q.get("volume"),
            "trade_value": q.get("trade_value"),
            "quote_time": q.get("quote_time"),
            "quote_source": q.get("quote_source"),
            "execution_status": status_code,
            "current_action": "禁止交易" if status_code == "OPEN_ENTRY_PASSED_NO_CHASE" else ("等待" if status_code != "OPEN_ENTRY_WINDOW" else "觀察"),
            "execution_note": status_text,
            "strategy_signal": True,
            "production_eligible": False,
            "strategy_status": "PREREGISTERED_CHALLENGER / NOT_PRODUCTION",
        }
        candidates.append(item)

    # Frozen portfolio ordering: descending RS percentile, then symbol.
    candidates.sort(key=lambda x: (-x["rs_pct"], x["symbol"]))
    candidates = candidates[:top_n]

    payload = {
        "generated_at": now.isoformat(),
        "command": "Sky Swing V1.1｜現在掃一次",
        "strategy": "Sky Swing Challenger V1.1",
        "strategy_status": "PREREGISTERED_CHALLENGER / NOT_PRODUCTION",
        "spec": "research/SKY_SWING_CHALLENGER_V1_1_PREREGISTRATION.md",
        "signal_date": signal_date,
        "execution_date": now.date().isoformat(),
        "historical_symbols_loaded": len(bysym),
        "signal_cross_section_count": len(cross),
        "breadth": breadth,
        "frozen_signal_count": len(frozen_pass),
        "date_selection": date_meta,
        "operational_full_market_scan": operational_full_market_scan,
        "strict_official_full_market_certified": False,
        "quote_coverage_pct": coverage,
        "universe_count": len(universe),
        "quote_count": len(quotes),
        "twse_quote_count": twse_n,
        "tpex_quote_count": tpex_n,
        "source_health": {
            "official_universe": universe_health,
            "intraday": {
                "source": "TWSE MIS TSE + OTC operational fallback",
                "note": "OTC is operational fallback, not TPEx-official real-time certification.",
            },
            "daily_history": {
                "source": "W3 canonical Swing daily artifact",
                "latest_signal_date": signal_date,
            },
        },
        "warnings": warnings,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "governance": [
            "V1.1 frozen rule is EOD signal at D close and D+1 open entry.",
            "Intraday current price never replaces the frozen D+1 open entry rule.",
            "V1.1 remains preregistered challenger / not Production.",
            "No threshold, stop, target, horizon, or ranking weight is changed by this live scanner.",
        ],
    }

    (OUT / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"Sky Swing V1.1｜現在掃一次｜{now:%Y-%m-%d %H:%M}",
        f"訊號日：{signal_date}｜執行日：{now:%Y-%m-%d}",
        f"全市場實務掃描：{'是' if operational_full_market_scan else '否'}｜覆蓋率 {coverage}%｜母池 {len(universe)}｜即時報價 {len(quotes)}",
        f"V1.1 cross-section：{len(cross)}｜Breadth：{round((breadth or 0)*100,2)}%｜凍結規則通過：{len(frozen_pass)}｜今日有效候選：{len(candidates)}",
        f"執行狀態：{status_code}｜{status_text}",
        "",
        render_mobile_table(candidates),
        "",
        "【治理】",
        "V1.1 仍為 PREREGISTERED_CHALLENGER / NOT_PRODUCTION；即時資料接通不等於 Promotion。",
        "盤中掃描不會把現價替代原凍結規則的 D+1 開盤進場。",
        "多方／空方評分為證據評分，不是勝率或機率。",
    ]
    text = "\n".join(lines)
    (OUT / "latest.txt").write_text(text, encoding="utf-8")
    print(text)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history-dir", required=True)
    ap.add_argument("--top-n", type=int, default=20)
    args = ap.parse_args()
    run(args.history_dir, args.top_n)


if __name__ == "__main__":
    main()
