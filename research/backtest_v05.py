
from __future__ import annotations
import argparse, csv, json, math, statistics
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path

SCAN_TIMES = [time(9,10), time(10,10), time(11,10), time(12,10), time(13,0)]

# Approximate Taiwan intraday round-trip cost assumption for pilot only.
# This is NOT a broker-specific actual cost. It is deliberately configurable.
DEFAULT_ROUND_TRIP_COST_PCT = 0.45

def parse_dt(s):
    return datetime.fromisoformat(s)

def group_by_day(bars):
    out = defaultdict(list)
    for b in bars:
        dt = parse_dt(b["date"])
        out[dt.date()].append({**b, "_dt": dt})
    for d in out:
        out[d].sort(key=lambda x: x["_dt"])
    return out

def prev_close_map(by_day):
    days = sorted(by_day)
    out = {}
    for i, d in enumerate(days):
        if i == 0 or not by_day[days[i-1]]:
            out[d] = None
        else:
            out[d] = float(by_day[days[i-1]][-1]["close"])
    return out

def snapshot(day_bars, scan_t, previous_close):
    xs = [x for x in day_bars if x["_dt"].time() <= scan_t]
    if len(xs) < 2 or previous_close in (None, 0):
        return None
    cur, prv = xs[-1], xs[-2]
    close = float(cur["close"])
    high = max(float(x["high"]) for x in xs)
    low = min(float(x["low"]) for x in xs)
    avg = cur.get("average")
    avg = float(avg) if avg is not None else None
    change_pct = (close / previous_close - 1) * 100
    avg_dist = (close / avg - 1) * 100 if avg else None
    range_pos = (close-low)/(high-low) if high > low else None
    cur_vol = float(cur.get("volume") or 0)
    prv_vol = float(prv.get("volume") or 0)
    vol_ratio = cur_vol/prv_vol if prv_vol > 0 else None

    anti = []
    if change_pct >= 8.0:
        anti.append("漲幅>=8%")
    if avg_dist is not None and avg_dist >= 4.0:
        anti.append("距均價>=4%")
    if (
        change_pct >= 6.0 and range_pos is not None and range_pos >= 0.92
        and avg_dist is not None and avg_dist >= 2.5
    ):
        anti.append("高檔貼近日高且乖離偏大")

    return {
        "index": len(xs)-1,
        "close": close,
        "change_pct": change_pct,
        "avg": avg,
        "avg_distance_pct": avg_dist,
        "above_avg": (close >= avg) if avg else None,
        "range_pos": range_pos,
        "volume_ratio": vol_ratio,
        "volume_confirm": bool(vol_ratio is not None and vol_ratio > 1.5),
        "anti_chase_pass": not anti,
        "anti_reasons": anti,
    }

def future_excursions(day_bars, idx, horizon_bars):
    if idx >= len(day_bars)-1:
        return None
    entry = float(day_bars[idx]["close"])
    end = min(len(day_bars)-1, idx+horizon_bars)
    future = day_bars[idx+1:end+1]
    if not future or entry <= 0:
        return None
    highs = [float(x["high"]) for x in future]
    lows = [float(x["low"]) for x in future]
    exit_px = float(future[-1]["close"])
    return {
        "future_ret_pct": (exit_px/entry-1)*100,
        "mfe_pct": (max(highs)/entry-1)*100,
        "mae_pct": (min(lows)/entry-1)*100,
    }

def metrics(rows, flag, cost_pct):
    xs = []
    for r in rows:
        if r.get(flag):
            gross = r["future_ret_pct"]
            xs.append({**r, "net_ret_pct": gross-cost_pct})
    if not xs:
        return {"n": 0}

    vals = [x["net_ret_pct"] for x in xs]
    wins = [x for x in vals if x > 0]
    losses = [x for x in vals if x < 0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    pf = gross_profit/gross_loss if gross_loss > 0 else None
    payoff = (
        statistics.mean(wins) / abs(statistics.mean(losses))
        if wins and losses else None
    )
    return {
        "n": len(vals),
        "win_rate": sum(x > 0 for x in vals)/len(vals),
        "expectancy_net_pct": statistics.mean(vals),
        "median_net_pct": statistics.median(vals),
        "profit_factor_net": pf,
        "avg_win_net_pct": statistics.mean(wins) if wins else None,
        "avg_loss_net_pct": statistics.mean(losses) if losses else None,
        "payoff_ratio": payoff,
        "avg_mfe_pct": statistics.mean(x["mfe_pct"] for x in xs),
        "avg_mae_pct": statistics.mean(x["mae_pct"] for x in xs),
    }

def evaluate_file(path: Path, horizon_bars: int):
    obj = json.loads(path.read_text(encoding="utf-8"))
    by_day = group_by_day(obj["data"])
    pc = prev_close_map(by_day)
    rows = []
    for d in sorted(by_day):
        for t in SCAN_TIMES:
            s = snapshot(by_day[d], t, pc[d])
            if not s:
                continue
            f = future_excursions(by_day[d], s["index"], horizon_bars)
            if not f:
                continue

            # Pilot baseline/candidate intentionally isolates new Anti-Chase effect.
            baseline = s["above_avg"] is True and s["change_pct"] > 0
            candidate = baseline and s["anti_chase_pass"]

            rows.append({
                "symbol": obj["symbol"],
                "day": str(d),
                "scan_time": t.strftime("%H:%M"),
                "baseline_v04_like": baseline,
                "candidate_v05": candidate,
                **s, **f,
            })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="research_data")
    ap.add_argument("--out", default="research_output")
    ap.add_argument("--horizon-bars", type=int, default=12, help="12 x 5m = 60m")
    ap.add_argument("--round-trip-cost-pct", type=float, default=DEFAULT_ROUND_TRIP_COST_PCT)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    rows = []
    files = sorted(data_dir.glob("*_5.json"))
    for p in files:
        if not p.name.startswith("_"):
            rows.extend(evaluate_file(p, args.horizon_bars))

    base = metrics(rows, "baseline_v04_like", args.round_trip_cost_pct)
    cand = metrics(rows, "candidate_v05", args.round_trip_cost_pct)

    filtered = [r for r in rows if r["baseline_v04_like"] and not r["candidate_v05"]]
    filtered_next = [r["future_ret_pct"] for r in filtered]

    verdict = "INSUFFICIENT"
    reasons = []
    if base.get("n",0) >= 30 and cand.get("n",0) >= 20:
        base_exp = base.get("expectancy_net_pct")
        cand_exp = cand.get("expectancy_net_pct")
        base_pf = base.get("profit_factor_net") or 0
        cand_pf = cand.get("profit_factor_net") or 0
        if cand_exp is not None and base_exp is not None:
            if cand_exp > base_exp and cand_pf >= base_pf:
                verdict = "PASS_TO_EXPANDED_BACKTEST"
                reasons.append("Candidate net expectancy improved and PF did not deteriorate.")
            elif cand_exp >= base_exp - 0.05 and cand_pf >= base_pf * 0.95:
                verdict = "REVISE"
                reasons.append("Candidate roughly preserved economics; expand/tune before deployment.")
            else:
                verdict = "REJECT_CURRENT_RULE"
                reasons.append("Candidate materially deteriorated net expectancy/PF in pilot.")
    else:
        reasons.append("Sample size below pilot threshold.")

    report = {
        "scope": "Pilot only — isolates Anti-Chase on selected symbols; not full-market scanner validation.",
        "horizon_minutes": args.horizon_bars*5,
        "round_trip_cost_assumption_pct": args.round_trip_cost_pct,
        "baseline_v04_like": base,
        "candidate_v05": cand,
        "filtered_count": len(filtered),
        "filtered_future_mean_pct": statistics.mean(filtered_next) if filtered_next else None,
        "verdict": verdict,
        "verdict_reasons": reasons,
        "limitations": [
            "Selected-symbol pilot is not a full-market backtest.",
            "Market Gate Proxy, full-market Sector RS, MTF, SSS, Phase, Setup+Trigger, EES and RR are not validated here.",
            "Cost is an explicit assumption, not broker-specific actual realized cost.",
            "A+ remains prohibited from this pilot alone."
        ]
    }

    (out/"pilot_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if rows:
        fields = sorted({k for r in rows for k in r})
        with (out/"pilot_rows.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w=csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(rows)

    md = [
        "# Sky v0.5 Pilot Backtest",
        "",
        f"- Verdict: **{verdict}**",
        f"- Horizon: {args.horizon_bars*5} minutes",
        f"- Cost assumption: {args.round_trip_cost_pct:.3f}%",
        "",
        "## Baseline v0.4-like",
        f"- n: {base.get('n')}",
        f"- Net expectancy: {base.get('expectancy_net_pct')}",
        f"- Net PF: {base.get('profit_factor_net')}",
        "",
        "## Candidate v0.5",
        f"- n: {cand.get('n')}",
        f"- Net expectancy: {cand.get('expectancy_net_pct')}",
        f"- Net PF: {cand.get('profit_factor_net')}",
        "",
        "## Limits",
        "- Pilot only; not full-market validation.",
        "- A+ cannot be produced from this result.",
    ]
    (out/"pilot_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
