"""Run the pre-registered BRK20 backtest on local daily-bar CSV files.

CSV format (one file per symbol, named <symbol>.csv):
    date,open,high,low,close,volume   (date as YYYY-MM-DD, ascending)

Usage:
    python3 run_backtest.py --data-dir data/daily --out results.json
"""

import argparse
import csv
import glob
import json
import os
from dataclasses import replace

import config
from engine import Bar, Signal, simulate_trade
from metrics import summarize
from strategy import brk20_signals


def load_bars(path: str) -> list[Bar]:
    bars = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bars.append(Bar(row["date"], float(row["open"]), float(row["high"]),
                            float(row["low"]), float(row["close"]), float(row["volume"])))
    bars.sort(key=lambda b: b.date)
    return bars


def run(data_dir: str, cost_rate: float, max_hold: int = 5) -> dict:
    """Return trades for every split, with a ranking cap of 3 signals per day."""
    all_trades = []
    per_symbol = {}
    for path in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
        symbol = os.path.splitext(os.path.basename(path))[0]
        bars = load_bars(path)
        per_symbol[symbol] = bars
        for sig in brk20_signals(symbol, bars):
            # Target = entry + 2R; the entry price is the next open. Resolve here.
            entry = bars[sig.signal_index + 1].open if sig.signal_index + 1 < len(bars) else None
            if entry is None or sig.stop >= entry:
                continue
            r = entry - sig.stop
            sig = replace(sig, target=entry + 2 * r)
            trade = simulate_trade(bars, sig, cost_rate, max_hold_bars=max_hold)
            if trade:
                all_trades.append((bars[sig.signal_index].date, sig, trade))

    # Ranking cap: at most 3 entries per signal date, strongest breakout first.
    by_day: dict[str, list] = {}
    for d, sig, tr in all_trades:
        by_day.setdefault(d, []).append((sig, tr))
    kept = []
    for d, items in by_day.items():
        def strength(item):
            sig, _ = item
            i = next(k for k, b in enumerate(per_symbol[sig.symbol]) if b.date == d)
            return per_symbol[sig.symbol][i].close / sig.max_accept
        items.sort(key=strength, reverse=True)
        kept.extend((d, tr) for _, tr in items[:3])

    return {"trades": kept}


def split_summary(trades: list, split_bounds: dict) -> dict:
    out = {}
    for name, (start, end) in split_bounds.items():
        nets = [tr.net_return for d, tr in trades if start <= d <= end]
        out[name] = summarize(nets)
    return out


def promotion_check(summaries_primary: dict, summaries_stress: dict) -> dict:
    v = summaries_primary["validation"]
    r = summaries_primary["research_test_2026"]
    vs = summaries_stress["validation"]

    def ok_pf(s):
        return s["profit_factor"] is not None and s["profit_factor"] >= 1.2

    checks = {
        "n_validation_ge_100": v["n"] >= 100,
        "n_research_test_ge_100": r["n"] >= 100,
        "expectancy_primary_validation_gt_0": (v["expectancy"] or 0) > 0,
        "expectancy_primary_research_test_gt_0": (r["expectancy"] or 0) > 0,
        "pf_primary_validation_ge_1_2": ok_pf(v),
        "pf_primary_research_test_ge_1_2": ok_pf(r),
        "expectancy_stress_validation_gt_0": (vs["expectancy"] or 0) > 0,
        # Concentration-by-month check is not implemented in v1; reported as a declared gap.
        "month_concentration_check": "NOT_IMPLEMENTED",
    }
    implemented_pass = all(v is True for k, v in checks.items() if k != "month_concentration_check")
    # PASS_RESEARCH is only possible when every pre-registered check is implemented and passes.
    # v1 does not implement the month-concentration check, so the verdict is never PASS here.
    verdict = ("NOT_EVALUABLE: month_concentration_check not implemented in v1"
               if implemented_pass else "FAIL")
    return {"checks": checks, "implemented_checks_pass": implemented_pass,
            "PASS_RESEARCH": verdict}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    prim = run(args.data_dir, config.COST_PRIMARY_ROUND_TRIP)["trades"]
    stress = run(args.data_dir, config.COST_STRESS_ROUND_TRIP)["trades"]
    s_prim = split_summary(prim, config.SPLITS)
    s_stress = split_summary(stress, config.SPLITS)
    result = {
        "prereg": "PREREGISTRATION_V1.md",
        "primary_cost": s_prim,
        "stress_cost": s_stress,
        "promotion": promotion_check(s_prim, s_stress),
        "declared_gaps": ["walk-forward", "regime", "ablation", "portfolio", "fresh_oos"],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result["promotion"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
