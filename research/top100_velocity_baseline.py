from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

SCAN_TIMES = ("09:15", "09:30", "09:50", "10:15")
TOP_POOL = 100
SELECT_N = 3
PRIMARY_COST = 0.0045
STRESS_COST = 0.0065
MAX_PRICE = 100.0
LIMIT_UP_GUARD = 0.095


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(str(s))


def _bar_map(rows):
    out = {}
    for b in rows or []:
        ts = str(b.get("date") or "")
        if ts:
            out[_dt(ts)] = b
    return out


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def build_shard_rows(history_root: str, out_csv: str) -> int:
    root = Path(history_root)
    output = []
    for path in sorted(root.rglob("*_5m.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        symbol = str(obj.get("symbol") or "")
        exchange = str(obj.get("exchange") or "")
        bars = _bar_map(obj.get("data") or [])
        if not symbol or not bars:
            continue

        by_day = defaultdict(list)
        for ts in sorted(bars):
            by_day[ts.date()].append(ts)

        days = sorted(by_day)
        prev_close_by_day = {}
        for i, day in enumerate(days):
            if i == 0:
                continue
            prev_day = days[i - 1]
            prev_close_by_day[day] = _f(bars[by_day[prev_day][-1]].get("close"))

        for day in days:
            prior_close = prev_close_by_day.get(day)
            if not prior_close or not math.isfinite(prior_close) or prior_close <= 0:
                continue

            tz = by_day[day][0].tzinfo
            for hhmm in SCAN_TIMES:
                h, m = map(int, hhmm.split(":"))
                decision = datetime(day.year, day.month, day.day, h, m, tzinfo=tz)
                cur_ts = decision - timedelta(minutes=5)
                prv_ts = decision - timedelta(minutes=10)
                entry_ts = decision
                exit_ts = decision + timedelta(minutes=55)

                if not all(ts in bars for ts in (cur_ts, prv_ts, entry_ts, exit_ts)):
                    continue

                cur = bars[cur_ts]
                prv = bars[prv_ts]
                entry_bar = bars[entry_ts]
                exit_bar = bars[exit_ts]

                cur_close = _f(cur.get("close"))
                prv_close = _f(prv.get("close"))
                cur_vol = _f(cur.get("volume"))
                prv_vol = _f(prv.get("volume"))
                entry = _f(entry_bar.get("open"))
                exitp = _f(exit_bar.get("close"))

                vals = (cur_close, prv_close, cur_vol, prv_vol, entry, exitp)
                if not all(math.isfinite(v) for v in vals):
                    continue
                if min(cur_close, prv_close, entry, exitp) <= 0 or prv_vol <= 0:
                    continue

                output.append({
                    "date": day.isoformat(),
                    "decision_time": hhmm,
                    "symbol": symbol,
                    "exchange": exchange,
                    "current_price": cur_close,
                    "current_return": cur_close / prior_close - 1.0,
                    "prior_return": prv_close / prior_close - 1.0,
                    "price_velocity": cur_close / prv_close - 1.0,
                    "volume_accel": cur_vol / prv_vol - 1.0,
                    "entry_price": entry,
                    "exit_price_60m": exitp,
                    "gross_return_60m": exitp / entry - 1.0,
                })

    output.sort(key=lambda r: (r["date"], r["decision_time"], r["symbol"]))
    p = Path(out_csv)
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "date", "decision_time", "symbol", "exchange", "current_price",
        "current_return", "prior_return", "price_velocity", "volume_accel",
        "entry_price", "exit_price_60m", "gross_return_60m"
    ]
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(output)
    return len(output)


def _reader(path: Path):
    fh = path.open("r", encoding="utf-8", newline="")
    rd = csv.DictReader(fh)
    try:
        for row in rd:
            yield ((row["date"], row["decision_time"], row["symbol"]), row)
    finally:
        fh.close()


def _percentiles(rows, key):
    ordered = sorted(range(len(rows)), key=lambda i: float(rows[i][key]))
    n = len(ordered)
    out = [0.0] * n
    if n <= 1:
        return [1.0] * n
    for rank, idx in enumerate(ordered):
        out[idx] = rank / (n - 1)
    return out


def _metrics(trades, net_key):
    rs = [float(x[net_key]) for x in trades]
    if not rs:
        return {
            "n": 0,
            "expectancy": None,
            "win_rate": None,
            "pf": None,
            "max_drawdown": None,
            "avg_win": None,
            "avg_loss": None,
        }

    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r < 0]
    pf = (sum(wins) / abs(sum(losses))) if losses else None

    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in rs:
        equity *= (1.0 + r)
        peak = max(peak, equity)
        max_dd = min(max_dd, equity / peak - 1.0)

    return {
        "n": len(rs),
        "expectancy": sum(rs) / len(rs),
        "win_rate": len(wins) / len(rs),
        "pf": pf,
        "max_drawdown": max_dd,
        "avg_win": (sum(wins) / len(wins)) if wins else None,
        "avg_loss": (sum(losses) / len(losses)) if losses else None,
    }


def aggregate_and_select(shard_csvs, out_trades: str, out_report: str):
    streams = [_reader(Path(p)) for p in shard_csvs]
    merged = heapq.merge(*streams, key=lambda x: x[0])
    trades = []
    seen_day = defaultdict(set)

    group_key = None
    group = []

    def flush(rows, key):
        if not rows:
            return

        rows = [dict(r) for r in rows]
        rows.sort(key=lambda r: float(r["current_return"]), reverse=True)
        for i, r in enumerate(rows, 1):
            r["current_rank"] = i

        prior_sorted = sorted(rows, key=lambda r: float(r["prior_return"]), reverse=True)
        prior_rank = {r["symbol"]: i for i, r in enumerate(prior_sorted, 1)}

        pool = []
        for r in rows:
            r["prior_rank"] = prior_rank[r["symbol"]]
            r["rank_velocity"] = r["prior_rank"] - r["current_rank"]

            if r["current_rank"] > TOP_POOL:
                continue
            if float(r["current_price"]) > MAX_PRICE:
                continue
            if float(r["current_return"]) >= LIMIT_UP_GUARD:
                continue
            if float(r["price_velocity"]) <= 0:
                continue
            if float(r["rank_velocity"]) <= 0:
                continue
            if float(r["volume_accel"]) <= 0:
                continue
            pool.append(r)

        if not pool:
            return

        pp = _percentiles(pool, "price_velocity")
        rp = _percentiles(pool, "rank_velocity")
        vp = _percentiles(pool, "volume_accel")

        for i, r in enumerate(pool):
            r["score"] = (pp[i] + rp[i] + vp[i]) / 3.0

        pool.sort(
            key=lambda r: (float(r["score"]), float(r["price_velocity"])),
            reverse=True,
        )

        day = key[0]
        picked = 0
        for r in pool:
            if r["symbol"] in seen_day[day]:
                continue
            seen_day[day].add(r["symbol"])
            gross = float(r["gross_return_60m"])
            r["net_return_045"] = gross - PRIMARY_COST
            r["net_return_065"] = gross - STRESS_COST
            trades.append(r)
            picked += 1
            if picked >= SELECT_N:
                break

    for _, row in merged:
        k = (row["date"], row["decision_time"])
        if group_key is None:
            group_key = k
        if k != group_key:
            flush(group, group_key)
            group = []
            group_key = k
        group.append(row)

    if group_key is not None:
        flush(group, group_key)

    p = Path(out_trades)
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in trades for k in r}) if trades else []
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if fields:
            w.writeheader()
            w.writerows(trades)

    dates = sorted({r["date"] for r in trades})
    folds = []
    if dates:
        cut1 = max(1, len(dates) // 3)
        cut2 = max(cut1 + 1, 2 * len(dates) // 3)
        spans = [dates[:cut1], dates[cut1:cut2], dates[cut2:]]

        for i, span in enumerate(spans, 1):
            subset = [
                r for r in trades
                if span and span[0] <= r["date"] <= span[-1]
            ]
            folds.append({
                "fold": i,
                "from": span[0] if span else None,
                "to": span[-1] if span else None,
                "primary": _metrics(subset, "net_return_045"),
                "stress": _metrics(subset, "net_return_065"),
            })

    report = {
        "schema_version": "TOP100_VELOCITY_BASELINE_V1_0",
        "status": "RESEARCH_EVIDENCE_ONLY",
        "frozen_spec": {
            "scan_times": list(SCAN_TIMES),
            "bar_minutes": 5,
            "top_pool": TOP_POOL,
            "select_n": SELECT_N,
            "price_velocity_lookback_minutes": 5,
            "rank_velocity_lookback_minutes": 5,
            "volume_acceleration": "latest_completed_5m_volume / prior_5m_volume - 1",
            "eligibility": "Top100 current-day return; price<=100; day_return<9.5%; positive price/rank/volume acceleration",
            "score": "equal-weight mean percentile of price velocity, rank velocity, volume acceleration",
            "entry": "open of 5m bar beginning at decision timestamp",
            "exit": "close after 60 minutes (12 x 5m bars)",
            "same_symbol_max_per_day": 1,
            "primary_round_trip_cost": PRIMARY_COST,
            "stress_round_trip_cost": STRESS_COST,
        },
        "all": {
            "primary": _metrics(trades, "net_return_045"),
            "stress": _metrics(trades, "net_return_065"),
        },
        "folds": folds,
        "trade_count": len(trades),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "governance": {
            "production_change": False,
            "no_parameter_search": True,
            "not_comparable_to_full_historical_v14_until_authoritative_v14_replay_exists": True,
            "promotion_requires_remaining_validation_gates": True,
        },
    }

    Path(out_report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("build-shard")
    a.add_argument("--history-root", required=True)
    a.add_argument("--out", required=True)

    b = sub.add_parser("aggregate")
    b.add_argument("--inputs", nargs="+", required=True)
    b.add_argument("--out-trades", required=True)
    b.add_argument("--out-report", required=True)

    args = ap.parse_args()

    if args.cmd == "build-shard":
        print(json.dumps({"rows": build_shard_rows(args.history_root, args.out)}))
    else:
        print(json.dumps(
            aggregate_and_select(args.inputs, args.out_trades, args.out_report),
            ensure_ascii=False,
            indent=2,
        ))


if __name__ == "__main__":
    main()
