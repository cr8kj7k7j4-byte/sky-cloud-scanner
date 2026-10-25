from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

AUDIT_DATES = ["2023-12-31", "2024-12-31", "2025-12-31", "2026-09-30"]
MIN_PIT_PRICE_COVERAGE_PCT = 95.0


def _contains(interval: dict, day: str) -> bool:
    start = str(interval.get("listed_from") or "")
    end = interval.get("listed_to")
    return bool(start and start <= day and (not end or day <= str(end)))


def load_price_ranges(history_dir: str) -> dict[str, dict]:
    """Load canonical daily or legacy 5-minute per-symbol JSON files.

    Canonical W3 handoff should prefer *_D.json. Legacy *_5.json remains
    supported only so the readiness report can quantify the pre-handoff gap.
    If both exist for a symbol, daily data takes precedence.
    """
    out = {}
    paths = list(Path(history_dir).glob("*_5.json")) + list(Path(history_dir).glob("*_D.json"))
    paths = sorted(paths, key=lambda p: (p.name.endswith("_D.json"), p.name))
    for p in paths:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            sym = str(obj.get("symbol") or p.name.split("_", 1)[0])
            dates = []
            for bar in obj.get("data") or []:
                raw = str(bar.get("date") or "")
                if not raw:
                    continue
                try:
                    dates.append(datetime.fromisoformat(raw).date().isoformat())
                except ValueError:
                    continue
            if dates:
                out[sym] = {
                    "min_date": min(dates),
                    "max_date": max(dates),
                    "bars": len(obj.get("data") or []),
                }
        except Exception:
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history-dir", required=True)
    ap.add_argument("--pit-json", required=True)
    ap.add_argument("--out", default="research_output_swing_pit_readiness")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    pit = json.loads(Path(args.pit_json).read_text(encoding="utf-8"))
    intervals = list(pit.get("intervals") or [])
    prices = load_price_ranges(args.history_dir)

    interval_valid = bool((pit.get("interval_validation") or {}).get("valid"))
    pit_gate = bool(pit.get("historical_universe_gate_pass"))
    rows = {}
    all_pass = bool(interval_valid and pit_gate and intervals)

    for day in AUDIT_DATES:
        eligible = sorted({
            str(x.get("symbol"))
            for x in intervals
            if x.get("symbol") and _contains(x, day)
        })
        covered = sorted([
            s for s in eligible
            if s in prices
            and prices[s]["min_date"] <= day
            and prices[s]["max_date"] >= day
        ])
        missing = sorted(set(eligible) - set(covered))
        pct = (len(covered) / len(eligible) * 100.0) if eligible else 0.0
        passed = bool(eligible and pct >= MIN_PIT_PRICE_COVERAGE_PCT)
        all_pass = all_pass and passed
        rows[day] = {
            "pit_symbols": len(eligible),
            "price_symbols_covered": len(covered),
            "coverage_pct": round(pct, 4),
            "pass": passed,
            "missing_sample": missing[:100],
        }

    status = "READY_FOR_CANONICAL_SWING_REPLAY" if all_pass else "BLOCKED_PRICE_HISTORY_COVERAGE"
    report = {
        "schema_version": "1.0",
        "status": status,
        "historical_universe_gate_pass": pit_gate,
        "interval_validation_pass": interval_valid,
        "pit_intervals": len(intervals),
        "history_symbols_available": len(prices),
        "minimum_required_coverage_pct": MIN_PIT_PRICE_COVERAGE_PCT,
        "audit_dates": rows,
        "governance": {
            "rule": "Do not run promotion-grade Swing replay on a current-universe subset.",
            "blocked_means": "Acquire historical OHLC for the canonical PIT membership before proceeding.",
        },
    }

    (out / "swing_pit_readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# W1 Swing PIT Price-History Readiness",
        "",
        f"- Status: **{status}**",
        f"- PIT universe gate: {'PASS' if pit_gate else 'FAIL'}",
        f"- Interval validation: {'PASS' if interval_valid else 'FAIL'}",
        f"- Canonical PIT intervals: {len(intervals):,}",
        f"- Historical price symbols available: {len(prices):,}",
        "",
        "| Date | PIT symbols | Price-covered | Coverage | Gate |",
        "|---|---:|---:|---:|---|",
    ]
    for day, x in rows.items():
        lines.append(
            f"| {day} | {x['pit_symbols']:,} | {x['price_symbols_covered']:,} | "
            f"{x['coverage_pct']:.2f}% | {'PASS' if x['pass'] else 'BLOCKED'} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- This is a data-readiness gate, not a profitability test.",
        "- A legacy 100-symbol current-universe artifact cannot be promoted as canonical PIT evidence.",
        "- If blocked, W1 must acquire/reconstruct price history for PIT members before Exit, Ablation and Portfolio promotion tests can be validly completed.",
    ]
    (out / "swing_pit_readiness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
