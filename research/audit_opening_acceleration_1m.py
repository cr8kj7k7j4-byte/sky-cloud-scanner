from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from research.download_pit_universe_intraday import load_pit_union


def active_on(item: dict, day: str) -> bool:
    a = str(item.get("history_required_from") or item.get("listed_from") or "")
    b = str(item.get("history_required_to") or item.get("listed_to") or "9999-12-31")
    return bool(a) and a <= day <= b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pit-intervals", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--from-date", required=True)
    ap.add_argument("--to-date", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    expected = load_pit_union(args.pit_intervals, args.from_date, args.to_date)
    expected_keys = {(x["exchange"], x["symbol"]) for x in expected}
    observed_symbols = set()
    observed_by_day = defaultdict(set)
    duplicates = []
    seen_symbol_day = set()
    parse_errors = []

    files = sorted(Path(args.data_root).rglob("*_opening_1m.json"))
    for p in files:
        try:
            x = json.loads(p.read_text(encoding="utf-8"))
            key = (str(x.get("exchange") or ""), str(x.get("symbol") or ""))
            if key not in expected_keys:
                continue
            days = x.get("days") or []
            if days:
                observed_symbols.add(key)
            for d in days:
                day = str(d.get("date") or "")
                if not day:
                    continue
                sd = (key[0], key[1], day)
                if sd in seen_symbol_day:
                    duplicates.append(sd)
                seen_symbol_day.add(sd)
                observed_by_day[day].add(key)
        except Exception as exc:
            parse_errors.append({"file": str(p), "error": f"{type(exc).__name__}: {exc}"})

    trading_days = sorted(observed_by_day)
    total_expected_sd = 0
    total_observed_sd = 0
    daily = {}
    for day in trading_days:
        exp = {k for k, item in zip([(x["exchange"],x["symbol"]) for x in expected], expected) if active_on(item, day)}
        obs = observed_by_day[day] & exp
        total_expected_sd += len(exp)
        total_observed_sd += len(obs)
        cov = len(obs) / len(exp) if exp else 0.0
        daily[day] = {"expected": len(exp), "observed": len(obs), "coverage_pct": round(cov*100,4)}

    symbol_cov = len(observed_symbols) / len(expected_keys) if expected_keys else 0.0
    sd_cov = total_observed_sd / total_expected_sd if total_expected_sd else 0.0
    min_daily = min((x["coverage_pct"] for x in daily.values()), default=0.0)

    report = {
        "schema_version": "OPENING_ACCELERATION_1M_COVERAGE_V1_0",
        "files": len(files),
        "expected_symbols": len(expected_keys),
        "symbols_with_data": len(observed_symbols),
        "symbol_coverage_pct": round(symbol_cov*100,4),
        "trading_days": len(trading_days),
        "expected_symbol_days": total_expected_sd,
        "observed_symbol_days": total_observed_sd,
        "symbol_day_coverage_pct": round(sd_cov*100,4),
        "minimum_daily_coverage_pct": round(min_daily,4),
        "duplicate_symbol_days": len(duplicates),
        "parse_errors": parse_errors[:100],
        "gate_95pct": bool(
            symbol_cov >= 0.95
            and sd_cov >= 0.95
            and min_daily >= 95.0
            and not duplicates
            and not parse_errors
        ),
        "daily": daily,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "daily"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
