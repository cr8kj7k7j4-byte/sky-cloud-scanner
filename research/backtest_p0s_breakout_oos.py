from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_COST_PCT = 0.45
DEFAULT_LOOKBACK = 4
DEFAULT_TARGET_R = 2.0
DEFAULT_MAX_ENTRY_R = 0.25
DEFAULT_MAX_HOLD_BARS = 24
MIN_RISK_PCT = 0.30
MAX_RISK_PCT = 2.50


def _dt(value):
    return datetime.fromisoformat(value)


def _f(row, key):
    value = row.get(key)
    return None if value in (None, "") else float(value)


def _group_days(data):
    out = defaultdict(list)
    for raw in data:
        try:
            row = dict(raw)
            row["_dt"] = _dt(row["date"])
            for key in ("open", "high", "low", "close"):
                row[key] = float(row[key])
            row["volume"] = float(row.get("volume") or 0)
            avg = row.get("average")
            row["average"] = None if avg in (None, "") else float(avg)
            out[row["_dt"].date()].append(row)
        except (KeyError, TypeError, ValueError):
            continue
    for day in out:
        out[day].sort(key=lambda x: x["_dt"])
    return out


def _plan(prior, target_r=DEFAULT_TARGET_R, max_entry_r=DEFAULT_MAX_ENTRY_R):
    trigger = max(x["high"] for x in prior)
    stop = min(x["low"] for x in prior)
    if trigger <= 0 or stop <= 0 or stop >= trigger:
        return None
    unit = trigger - stop
    return {
        "trigger": trigger,
        "stop": stop,
        "target": trigger + target_r * unit,
        "max_entry": trigger + max_entry_r * unit,
        "plan_risk": unit,
    }


def _entry_on_bar(bar, plan):
    trigger = plan["trigger"]
    max_entry = plan["max_entry"]
    if bar["high"] < trigger:
        return None
    entry = bar["open"] if bar["open"] >= trigger else trigger
    if entry > max_entry:
        return None
    return entry


def _simulate(bars, i, plan, entry, cost_pct, max_hold_bars):
    stop = plan["stop"]
    target = plan["target"]
    risk = entry - stop
    if risk <= 0:
        return None

    risk_pct = risk / entry * 100.0
    if not (MIN_RISK_PCT <= risk_pct <= MAX_RISK_PCT):
        return None

    gross_rr = (target - entry) / risk
    if gross_rr <= 0:
        return None

    end = min(len(bars) - 1, i + max_hold_bars)
    exit_px = bars[end]["close"]
    exit_reason = "TIME"
    exit_i = end
    mfe = None
    mae = None

    # Conservative 5m ambiguity rule: once filled, if the same bar or a later
    # bar touches stop and target, assume stop occurred first.
    for j in range(i, end + 1):
        hi = bars[j]["high"]
        lo = bars[j]["low"]
        mfe_j = (hi - entry) / risk
        mae_j = (lo - entry) / risk
        mfe = mfe_j if mfe is None else max(mfe, mfe_j)
        mae = mae_j if mae is None else min(mae, mae_j)

        stop_hit = lo <= stop
        target_hit = hi >= target
        if stop_hit:
            exit_px = stop
            exit_reason = "STOP_AMBIGUOUS" if target_hit else "STOP"
            exit_i = j
            break
        if target_hit:
            exit_px = target
            exit_reason = "TARGET"
            exit_i = j
            break

    gross_r = (exit_px - entry) / risk
    cost_r = float(cost_pct) / risk_pct
    net_r = gross_r - cost_r

    return {
        "entry": entry,
        "stop": stop,
        "target": target,
        "max_entry": plan["max_entry"],
        "risk_pct": risk_pct,
        "gross_rr_at_entry": gross_rr,
        "gross_r": gross_r,
        "cost_r": cost_r,
        "net_r": net_r,
        "mfe_r": mfe,
        "mae_r": mae,
        "bars_held": exit_i - i,
        "exit_reason": exit_reason,
    }


def scan_file(path, cost_pct=DEFAULT_COST_PCT, lookback=DEFAULT_LOOKBACK,
              target_r=DEFAULT_TARGET_R, max_entry_r=DEFAULT_MAX_ENTRY_R,
              max_hold_bars=DEFAULT_MAX_HOLD_BARS):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    symbol = str(obj.get("symbol") or Path(path).stem.split("_")[0])
    by_day = _group_days(obj.get("data", []))
    trades = []

    for day, bars in sorted(by_day.items()):
        used = False
        for i in range(lookback, len(bars)):
            if used:
                break
            prior = bars[i - lookback:i]
            plan = _plan(prior, target_r=target_r, max_entry_r=max_entry_r)
            if not plan:
                continue

            # Match online builder's average-price guard using the latest
            # available average at decision time.
            avg = bars[i - 1].get("average")
            if avg is not None and plan["trigger"] < avg:
                continue

            entry = _entry_on_bar(bars[i], plan)
            if entry is None or entry > 100:
                continue

            sim = _simulate(
                bars, i, plan, entry, cost_pct=cost_pct,
                max_hold_bars=max_hold_bars,
            )
            if sim is None:
                continue

            trades.append({
                "symbol": symbol,
                "date": str(day),
                "trigger_time": bars[i]["_dt"].strftime("%H:%M"),
                **sim,
            })
            used = True

    return trades


def metrics(rows):
    if not rows:
        return {"n": 0}
    vals = [float(x["net_r"]) for x in rows]
    wins = [x for x in vals if x > 0]
    losses = [x for x in vals if x < 0]
    gp = sum(wins)
    gl = -sum(losses)
    return {
        "n": len(vals),
        "win_rate": round(sum(x > 0 for x in vals) / len(vals), 4),
        "expectancy_r": round(statistics.mean(vals), 4),
        "median_r": round(statistics.median(vals), 4),
        "pf": round(gp / gl, 4) if gl > 0 else None,
        "avg_win_r": round(statistics.mean(wins), 4) if wins else None,
        "avg_loss_r": round(statistics.mean(losses), 4) if losses else None,
        "avg_mfe_r": round(statistics.mean(
            x["mfe_r"] for x in rows if x["mfe_r"] is not None
        ), 4),
        "avg_mae_r": round(statistics.mean(
            x["mae_r"] for x in rows if x["mae_r"] is not None
        ), 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="research_data/history")
    ap.add_argument("--cutoff", required=True,
                    help="First OOS date, e.g. 2026-01-01")
    ap.add_argument("--cost-pct", type=float, default=DEFAULT_COST_PCT)
    ap.add_argument("--out", default="research_output_p0s_oos")
    args = ap.parse_args()

    files = sorted(Path(args.data_dir).glob("*_5.json"))
    trades = []
    for path in files:
        trades.extend(scan_file(path, cost_pct=args.cost_pct))

    cutoff = args.cutoff
    ins = [x for x in trades if x["date"] < cutoff]
    oos = [x for x in trades if x["date"] >= cutoff]

    report = {
        "strategy": "P0-S 5m breakout candidate",
        "production_eligible": False,
        "rules": {
            "lookback_bars": DEFAULT_LOOKBACK,
            "target_r": DEFAULT_TARGET_R,
            "max_entry_r": DEFAULT_MAX_ENTRY_R,
            "cost_pct": args.cost_pct,
            "max_hold_bars": DEFAULT_MAX_HOLD_BARS,
            "risk_bounds_pct": [MIN_RISK_PCT, MAX_RISK_PCT],
            "intrabar_rule": "stop-first when stop and target touch same 5m bar",
        },
        "cutoff": cutoff,
        "input_files": len(files),
        "all": metrics(trades),
        "in_sample": metrics(ins),
        "oos": metrics(oos),
        "promotion_gate": {
            "min_oos_n": 100,
            "min_oos_pf": 1.05,
            "min_oos_expectancy_r": 0.0,
        },
        "limitations": [
            "Historical 5m OHLC cannot reconstruct exact intrabar path.",
            "Fixed round-trip cost assumption is a stress proxy, not exact fill cost.",
            "Current historical universe may contain survivorship bias.",
            "Passing this gate does not authorize live trading or A+ classification.",
        ],
    }

    o = report["oos"]
    passed = (
        o.get("n", 0) >= report["promotion_gate"]["min_oos_n"]
        and (o.get("pf") or 0) >= report["promotion_gate"]["min_oos_pf"]
        and (o.get("expectancy_r") or -999) > report["promotion_gate"]["min_oos_expectancy_r"]
    )
    report["verdict"] = "PASS_TO_PAPER_TRADING" if passed else "RESEARCH_ONLY"

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "p0s_oos_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = [
        "# P0-S 5m Breakout OOS Validation",
        f"- Verdict: **{report['verdict']}**",
        f"- Cutoff: {cutoff}",
        f"- Input files: {len(files)}",
        f"- In-sample: {report['in_sample']}",
        f"- OOS: {report['oos']}",
        "",
        "Research only. A+ / live promotion remains prohibited until Paper Trading and governance gates pass.",
    ]
    (out / "p0s_oos_summary.md").write_text("\n".join(summary), encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
