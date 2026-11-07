"""Fugle Developer 0050 fixed-rule historical replay, cost matched to FinMind pilot.

This is NOT an event, MCR, or positive-expectancy backtest. The original
research MA60/MOM20 definition is reused without retuning on Fugle prices.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
from research.fugle_historical_evidence_audit import candles, clean_rows

START = "2025-11-10"
END = "2026-11-06"
MA = 60
MOM = 20
COSTS = (0.0045, 0.0065)
FINMIND_PILOT_REPORTED = {
    "0.0045": {"TREND": 38.3747, "BUY_HOLD": 46.9623},
    "0.0065": {"TREND": 35.6347, "BUY_HOLD": 46.8158},
}


def load_fugle_0050(key):
    rows = {}
    statuses = []
    # The vendor rejects windows equal to or exceeding one calendar year.
    for start, end in (("2025-08-01", "2026-04-30"),
                       ("2026-05-01", END)):
        payload, state = candles(key, "0050", start, end, adjusted=False)
        parsed, quality = clean_rows(payload)
        statuses.append({"window": [start, end], "http": state, "quality": quality})
        rows.update({d: (d, r["open"], r["close"]) for d, r in parsed.items()})
    return [rows[d] for d in sorted(rows)], statuses


def simulate(data, cost, mode):
    cash, shares = 1.0, 0.0
    nav = []
    transactions = []
    close = [bar[2] for bar in data]
    for i, (d, op, cl) in enumerate(data):
        if i and d >= START:
            previous = i - 1
            should_hold = mode == "BUY_HOLD"
            if mode == "TREND":
                should_hold = False
                if previous >= MA - 1 and previous >= MOM:
                    ma60 = sum(close[previous - MA + 1:previous + 1]) / MA
                    momentum = close[previous] / close[previous - MOM] - 1
                    should_hold = close[previous] > ma60 and momentum > 0
            if should_hold and shares == 0:
                shares = cash / (op * (1 + cost / 2))
                cash = 0.0
                transactions.append({"session": d, "side": "BUY"})
            elif not should_hold and shares > 0:
                cash = shares * op * (1 - cost / 2)
                shares = 0.0
                transactions.append({"session": d, "side": "SELL"})
        if d >= START:
            nav.append((d, cash + shares * cl))
    if not nav:
        return {"n_sessions": 0}
    peak = nav[0][1]
    drawdown = 0.0
    for _, capital in nav:
        peak = max(peak, capital)
        drawdown = min(drawdown, capital / peak - 1)
    return {
        "n_sessions": len(nav),
        "return_pct": round(100 * (nav[-1][1] - 1), 4),
        "max_mark_to_market_drawdown_pct": round(100 * drawdown, 4),
        "entry_count": sum(t["side"] == "BUY" for t in transactions),
        "exit_count": sum(t["side"] == "SELL" for t in transactions),
        "final_position_unrealized": bool(shares),
        "start_date": nav[0][0], "end_date": nav[-1][0],
    }


def run(key):
    out = {
        "model": "FUGLE_0050_FIXED_TREND_REPLAY",
        "status": "INSUFFICIENT_DATA",
        "production_signal": False,
        "independent_oos": False,
        "signal_rule": "previous close > 60-session SMA and previous 20-session return positive",
        "period": [START, END],
        "no_reoptimization": True,
        "no_dividend_total_return_proof": True,
        "source": "Fugle historical raw daily OHLCV",
        "api": [], "rows": 0, "results": {},
        "known_prior_finmind_pilot_reference": FINMIND_PILOT_REPORTED,
    }
    if not key:
        out["blocked"] = "FUGLE_API_KEY_NOT_CONFIGURED"
        return out
    data, out["api"] = load_fugle_0050(key)
    out["rows"] = len(data)
    if len(data) < 100:
        out["blocked"] = "INSUFFICIENT_REPLAY_DAYS"
        return out
    for cost in COSTS:
        key_cost = str(cost)
        measurements = {mode: simulate(data, cost, mode)
                        for mode in ("TREND", "BUY_HOLD")}
        out["results"][key_cost] = measurements
        out.setdefault("delta_vs_prior_finmind_pilot_pct_points", {})[key_cost] = {
            mode: round(measurements[mode]["return_pct"] -
                        FINMIND_PILOT_REPORTED[key_cost][mode], 4)
            for mode in measurements
        }
    out["comparison_note"] = (
        "Prior FinMind pilot is historical previously observed result; "
        "matching pilot results validates input/source reproducibility, not profitable alpha."
    )
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="research_output/fugle_0050_fixed_trend_replay.json")
    args = p.parse_args()
    result = run(os.getenv("FUGLE_API_KEY", "").strip())
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "rows": result["rows"],
        "results": result["results"],
        "delta_vs_prior_finmind_pilot_pct_points": result.get(
            "delta_vs_prior_finmind_pilot_pct_points"),
        "api": result["api"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
