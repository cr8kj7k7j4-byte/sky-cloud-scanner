from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

AUDIT_DATES = ["2023-12-31", "2024-12-31", "2025-12-31", "2026-09-30"]
MIN_COVERAGE = 95.0


def _contains(interval: dict, day: str) -> bool:
    start = str(interval.get("listed_from") or "")
    end = interval.get("listed_to")
    return bool(start and start <= day and (not end or day <= str(end)))


def load_history(history_dir: str):
    meta = {}
    observed_dates = defaultdict(set)
    duplicates = []
    invalid = []
    adjusted_false = []
    source_counts = defaultdict(int)

    for p in sorted(Path(history_dir).glob("*_D.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            sym = str(obj.get("symbol") or p.stem.split("_", 1)[0])
            dates = []
            seen = set()
            for bar in obj.get("data") or []:
                day = str(bar.get("date") or bar.get("trading_date") or "")
                if not day:
                    continue
                try:
                    datetime.fromisoformat(day)
                except ValueError:
                    invalid.append({"symbol": sym, "date": day, "reason": "invalid_date"})
                    continue
                key = (str(bar.get("exchange") or ""), day)
                if key in seen:
                    duplicates.append({"symbol": sym, "exchange": key[0], "date": day})
                    continue
                seen.add(key)
                if bar.get("adjusted") is not True:
                    adjusted_false.append({"symbol": sym, "date": day})
                for f in ("open", "high", "low", "close"):
                    try:
                        if float(bar.get(f)) <= 0:
                            raise ValueError
                    except Exception:
                        invalid.append({"symbol": sym, "date": day, "reason": f"invalid_{f}"})
                try:
                    if int(bar.get("volume")) < 0:
                        raise ValueError
                except Exception:
                    invalid.append({"symbol": sym, "date": day, "reason": "invalid_volume"})
                dates.append(day)
                observed_dates[sym].add(day)
                source_counts[str(bar.get("source") or obj.get("source") or "unknown")] += 1
            if dates:
                meta[sym] = {
                    "min_date": min(dates),
                    "max_date": max(dates),
                    "bars": len(dates),
                    "adjusted": bool(obj.get("adjusted")),
                    "source": obj.get("source"),
                    "sha256": obj.get("sha256"),
                }
        except Exception as exc:
            invalid.append({"file": str(p), "reason": f"parse_error:{type(exc).__name__}"})

    return meta, observed_dates, duplicates, invalid, adjusted_false, dict(source_counts)


def compress_missing(days: list[str]) -> list[dict]:
    if not days:
        return []
    # Missing trading dates are not forward-filled. We preserve explicit dates;
    # compact into year-month buckets to keep reports bounded.
    buckets = defaultdict(list)
    for d in days:
        buckets[d[:7]].append(d)
    return [
        {
            "month": month,
            "missing_days": len(vals),
            "first": min(vals),
            "last": max(vals),
            "reason": "NO_BAR_NO_FORWARD_FILL__MAY_BE_SUSPENSION_NO_TRADE_OR_SOURCE_GAP",
        }
        for month, vals in sorted(buckets.items())
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history-dir", required=True)
    ap.add_argument("--pit-json", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pit = json.loads(Path(args.pit_json).read_text(encoding="utf-8"))
    intervals = list(pit.get("intervals") or [])
    history, observed_dates, duplicates, invalid, adjusted_false, source_counts = load_history(args.history_dir)

    all_dates = sorted({d for values in observed_dates.values() for d in values})
    audit_rows = {}
    all_pass = bool(
        pit.get("historical_universe_gate_pass")
        and (pit.get("interval_validation") or {}).get("valid")
        and not duplicates
        and not adjusted_false
    )

    for day in AUDIT_DATES:
        eligible = sorted({
            str(x.get("symbol"))
            for x in intervals
            if x.get("symbol") and _contains(x, day)
        })
        covered = sorted([
            s for s in eligible
            if s in history
            and history[s]["min_date"] <= day
            and history[s]["max_date"] >= day
            and history[s]["adjusted"]
        ])
        missing = sorted(set(eligible) - set(covered))
        pct = (len(covered) / len(eligible) * 100.0) if eligible else 0.0
        passed = bool(eligible and pct >= MIN_COVERAGE)
        all_pass = all_pass and passed
        audit_rows[day] = {
            "pit_symbols": len(eligible),
            "price_symbols_covered": len(covered),
            "coverage_pct": round(pct, 4),
            "pass": passed,
            "missing_symbols": missing,
        }

    # Symbol-day missingness on the observed market-date union.
    expected = 0
    observed = 0
    missing_by_symbol = {}
    interval_by_symbol = defaultdict(list)
    for x in intervals:
        if x.get("symbol"):
            interval_by_symbol[str(x["symbol"])].append(x)

    for symbol, ints in sorted(interval_by_symbol.items()):
        expected_days = [
            d for d in all_dates
            if any(_contains(i, d) for i in ints)
        ]
        actual = observed_dates.get(symbol, set())
        missing = [d for d in expected_days if d not in actual]
        expected += len(expected_days)
        observed += len(expected_days) - len(missing)
        if missing:
            missing_by_symbol[symbol] = compress_missing(missing)

    symbol_day_coverage = (observed / expected * 100.0) if expected else 0.0

    report = {
        "schema_version": "SWING_PIT_PRICE_COVERAGE_1.1",
        "status": "READY_FOR_W1_CANONICAL_REPLAY" if all_pass else "BLOCKED_PRICE_HISTORY_COVERAGE",
        "canonical_pit_intervals": len(intervals),
        "canonical_pit_unique_symbols": len({str(x.get("symbol")) for x in intervals if x.get("symbol")}),
        "price_symbols_available": len(history),
        "audit_dates": audit_rows,
        "minimum_required_audit_date_coverage_pct": MIN_COVERAGE,
        "symbol_day_expected": expected,
        "symbol_day_observed": observed,
        "symbol_day_coverage_pct": round(symbol_day_coverage, 4),
        "duplicates": duplicates,
        "invalid_rows": invalid[:500],
        "adjusted_false_rows": adjusted_false[:500],
        "source_counts": source_counts,
        "missingness_by_symbol": missing_by_symbol,
        "governance": {
            "current_universe_substitution_forbidden": True,
            "forward_fill": False,
            "corporate_action_policy": "Raw FinMind TaiwanStockPrice OHLC is backward-adjusted by Sky using free reference datasets for dividend/right, capital reduction, stock split and par-value change. Same-date multi-dataset conflicts fail closed. PIT membership remains canonical official TWSE/TPEx intervals.",
            "market_transfer_policy": "Exchange is assigned per canonical interval on each trading date.",
            "missing_policy": "No forward fill. Missing eligible dates remain explicit audit gaps.",
        },
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "coverage_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# W3 Swing Canonical PIT Daily Price Coverage",
        "",
        f"- Status: **{report['status']}**",
        f"- Canonical PIT intervals: {len(intervals):,}",
        f"- Canonical PIT unique symbols: {report['canonical_pit_unique_symbols']:,}",
        f"- Price symbols available: {len(history):,}",
        f"- Symbol-day coverage: {symbol_day_coverage:.2f}%",
        f"- Duplicate symbol/exchange/date rows: {len(duplicates):,}",
        f"- Non-adjusted rows: {len(adjusted_false):,}",
        "",
        "| Audit date | PIT symbols | Price-covered | Coverage | Gate |",
        "|---|---:|---:|---:|---|",
    ]
    for day, x in audit_rows.items():
        lines.append(
            f"| {day} | {x['pit_symbols']:,} | {x['price_symbols_covered']:,} | "
            f"{x['coverage_pct']:.2f}% | {'PASS' if x['pass'] else 'BLOCKED'} |"
        )
    lines += [
        "",
        "## Corporate actions",
        "",
        "- Price source uses FinMind TaiwanStockPriceAdj adjusted OHLC series.",
        "- FinMind announced a full historical recomputation in 2026-09 covering ex-right/ex-dividend holiday shifts, capital reductions and combined events.",
        "- No synthetic adjustment factor is inferred by Sky.",
        "",
        "## Missingness",
        "",
        "- No missing eligible date is forward-filled.",
        "- Missing dates are preserved for W1 bias review; suspension/no-trade/source-gap remain distinct from fabricated bars.",
        "",
        "## PIT / continuity",
        "",
        "- Membership comes only from canonical pit_intervals.json.",
        "- TWSE/TPEx exchange assignment is resolved per historical interval and per date.",
        "- Today's current universe is never substituted for historical membership.",
    ]
    (out / "coverage_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    if report["status"] != "READY_FOR_W1_CANONICAL_REPLAY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
