from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from research.build_universe_sample import fetch_universe
from src.official_universe_events import collect_official_events
from src.point_in_time_universe import (
    survivorship_audit,
    universe_as_of,
    validate_intervals,
)

MIN_CURRENT_INTERVAL_COVERAGE_PCT = 99.0
REQUIRED_HISTORICAL_SOURCES = {"TWSE_DELIST", "TPEX_DELIST"}

DEFAULT_DATES = [
    "2023-12-31",
    "2024-12-31",
    "2025-12-31",
    "2026-09-30",
]


def build_historical_universe_audit(
    *,
    official_payload: dict,
    current_universe: list[dict],
    audit_dates: list[str],
) -> dict:
    intervals = list(official_payload.get("intervals") or [])
    unresolved = list(official_payload.get("unresolved") or [])
    source_health = list(official_payload.get("health") or [])
    validation = validate_intervals(intervals)

    current_by_exchange = defaultdict(set)
    for row in current_universe:
        symbol = str(row.get("symbol") or "")
        exchange = str(row.get("exchange") or "")
        if symbol and exchange:
            current_by_exchange[exchange].add(symbol)

    interval_by_exchange = defaultdict(set)
    for row in intervals:
        symbol = str(row.get("symbol") or "")
        exchange = str(row.get("exchange") or "")
        if symbol and exchange:
            interval_by_exchange[exchange].add(symbol)

    current_coverage = {}
    for exchange in sorted(set(current_by_exchange) | set(interval_by_exchange)):
        current = current_by_exchange.get(exchange, set())
        known = interval_by_exchange.get(exchange, set())
        covered = current & known
        missing = sorted(current - known)
        current_coverage[exchange] = {
            "current_symbols": len(current),
            "symbols_with_listing_interval": len(covered),
            "coverage_pct": round((len(covered) / len(current) * 100.0), 4) if current else 0.0,
            "missing_current_symbols": missing[:200],
        }

    dates = {}
    for d in audit_dates:
        pit = universe_as_of(intervals, d)
        by_exchange = defaultdict(set)
        for row in pit:
            by_exchange[row["exchange"]].add(row["symbol"])

        exchange_reports = {}
        for exchange in sorted(set(current_by_exchange) | set(by_exchange)):
            current = current_by_exchange.get(exchange, set())
            historical = by_exchange.get(exchange, set())
            x = survivorship_audit(
                current_symbols=current,
                pit_symbols=historical,
            )
            exchange_reports[exchange] = {
                "current_n": x["current_n"],
                "pit_n": x["pit_n"],
                "historical_names_missing_from_current_n": len(
                    x["historical_names_missing_from_current_universe"]
                ),
                "current_names_not_yet_listed_n": len(
                    x["current_names_not_in_historical_universe"]
                ),
                "historical_names_missing_from_current_sample":
                    x["historical_names_missing_from_current_universe"][:100],
                "current_names_not_yet_listed_sample":
                    x["current_names_not_in_historical_universe"][:100],
                "survivorship_bias_present": x["survivorship_bias_present"],
            }

        dates[d] = {
            "pit_symbols_total": len(pit),
            "by_exchange": exchange_reports,
        }

    sources_ok = bool(source_health) and all(x.get("ok") for x in source_health)
    health_by_name = {str(x.get("source")): x for x in source_health}
    historical_source_coverage_ok = all(
        name in health_by_name
        and health_by_name[name].get("ok")
        and int(health_by_name[name].get("parsed_events") or 0) > 0
        for name in REQUIRED_HISTORICAL_SOURCES
    )
    current_coverage_ok = all(
        x["coverage_pct"] >= MIN_CURRENT_INTERVAL_COVERAGE_PCT
        for x in current_coverage.values()
        if x["current_symbols"] > 0
    )
    unresolved_ok = len(unresolved) == 0
    historical_dates_nonempty = bool(dates) and all(
        int(item.get("pit_symbols_total") or 0) > 0
        for item in dates.values()
    )

    gate_pass = bool(
        sources_ok
        and historical_source_coverage_ok
        and validation.get("valid")
        and current_coverage_ok
        and unresolved_ok
        and historical_dates_nonempty
    )

    return {
        "schema_version": "1.0",
        "source_health": source_health,
        "events": len(official_payload.get("events") or []),
        "intervals": len(intervals),
        "unresolved": len(unresolved),
        "interval_validation": validation,
        "current_interval_coverage": current_coverage,
        "historical_dates": dates,
        "historical_source_coverage_ok": historical_source_coverage_ok,
        "historical_dates_nonempty": historical_dates_nonempty,
        "historical_universe_gate_pass": gate_pass,
        "production_eligible": gate_pass,
        "status": (
            "HISTORICAL_UNIVERSE_PASS"
            if gate_pass
            else "HISTORICAL_UNIVERSE_INCOMPLETE"
        ),
        "governance": {
            "minimum_current_interval_coverage_pct": MIN_CURRENT_INTERVAL_COVERAGE_PCT,
            "all_official_sources_must_be_healthy": True,
            "required_historical_sources": sorted(REQUIRED_HISTORICAL_SOURCES),
            "required_historical_sources_must_parse_events": True,
            "all_audit_dates_must_have_nonzero_pit_membership": True,
            "unresolved_events_allowed": 0,
            "rule": (
                "Current-universe-only historical studies must not be promoted "
                "while the historical-universe gate is incomplete."
            ),
        },
    }


def write_markdown(report: dict, path: Path):
    lines = [
        "# Historical Universe / Survivorship Audit",
        "",
        f"- Events: {report['events']:,}",
        f"- Intervals: {report['intervals']:,}",
        f"- Unresolved events: {report['unresolved']:,}",
        f"- Interval validation: {'PASS' if report['interval_validation']['valid'] else 'FAIL'}",
        f"- Historical source coverage: {'PASS' if report['historical_source_coverage_ok'] else 'FAIL'}",
        f"- Historical dates non-empty: {'PASS' if report['historical_dates_nonempty'] else 'FAIL'}",
        f"- Historical Universe Gate: {'PASS' if report['historical_universe_gate_pass'] else 'FAIL'}",
        "",
        "## Current-universe interval coverage",
        "",
        "| Exchange | Current | Covered by interval | Coverage |",
        "|---|---:|---:|---:|",
    ]
    for exchange, x in report["current_interval_coverage"].items():
        lines.append(
            f"| {exchange} | {x['current_symbols']:,} | "
            f"{x['symbols_with_listing_interval']:,} | {x['coverage_pct']:.4f}% |"
        )

    for d, item in report["historical_dates"].items():
        lines += [
            "",
            f"## {d}",
            "",
            f"- PIT symbols total: {item['pit_symbols_total']:,}",
            "",
            "| Exchange | Current N | PIT N | Historical names absent today | Current names not yet listed | Bias |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for exchange, x in item["by_exchange"].items():
            lines.append(
                f"| {exchange} | {x['current_n']:,} | {x['pit_n']:,} | "
                f"{x['historical_names_missing_from_current_n']:,} | "
                f"{x['current_names_not_yet_listed_n']:,} | "
                f"{'YES' if x['survivorship_bias_present'] else 'NO'} |"
            )

    lines += [
        "",
        "## Governance",
        "",
        "- Historical studies using today's listing universe are survivorship-biased whenever PIT membership differs.",
        "- Promotion requires healthy official sources, valid non-overlapping intervals, no unresolved delisting events, and >=99% current-symbol interval coverage per exchange.",
        "- Failure blocks promotion; it does not invalidate descriptive research.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", nargs="*", default=DEFAULT_DATES)
    ap.add_argument("--out", default="output/historical_universe_audit")
    args = ap.parse_args()

    official = collect_official_events()
    current = fetch_universe()
    report = build_historical_universe_audit(
        official_payload=official,
        current_universe=current,
        audit_dates=args.dates,
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(report, out / "audit.md")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
