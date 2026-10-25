from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from research.build_universe_sample import fetch_universe
from src.official_universe_events import collect_official_events, reconcile_cross_exchange_migrations
from src.point_in_time_universe import (
    survivorship_audit,
    universe_as_of,
    validate_intervals,
)

MIN_CURRENT_INTERVAL_COVERAGE_PCT = 99.0
REQUIRED_HISTORICAL_SOURCES = {"TWSE_DELIST", "TPEX_DELIST"}
WINDOW_START = "2023-01-01"
LISTING_HISTORY_START = {"TWSE": "2000-01-01", "TPEx": "2005-01-01"}

DEFAULT_DATES = [
    "2023-12-31",
    "2024-12-31",
    "2025-12-31",
    "2026-09-30",
]



def build_windowed_intervals(events: list[dict], window_start: str = WINDOW_START) -> dict:
    """Build membership intervals only for the governed research window."""
    grouped=defaultdict(list)
    for raw in events or []:
        symbol=str(raw.get("symbol") or "")
        exchange=str(raw.get("exchange") or "")
        event_type=str(raw.get("event_type") or "")
        event_date=str(raw.get("event_date") or "")
        if symbol and exchange and event_type in {"LIST","DELIST"} and event_date:
            grouped[(symbol,exchange)].append(raw)

    intervals=[]
    unresolved=[]
    annotations=[]

    # Resolve market membership at the governed-window start BEFORE clipping
    # dates to window_start. If the same symbol appears active on both exchanges
    # because one market's termination event is absent, the later official LIST
    # on the other exchange is affirmative migration evidence.
    prewindow_state={}
    for (symbol,exchange), arr in grouped.items():
        arr_sorted=sorted(
            arr,
            key=lambda x: (
                str(x.get("event_date")),
                0 if x.get("event_type")=="DELIST" else 1,
            ),
        )
        listed=False
        last_list=None
        for e in arr_sorted:
            d=str(e.get("event_date"))
            if d >= window_start:
                break
            if e.get("event_type")=="LIST":
                listed=True
                last_list=d
            elif e.get("event_type")=="DELIST":
                listed=False
        prewindow_state[(symbol,exchange)]={"listed":listed,"last_list":last_list}

    by_symbol_prewindow=defaultdict(list)
    for (symbol,exchange), state in prewindow_state.items():
        if state["listed"]:
            by_symbol_prewindow[symbol].append((exchange,state.get("last_list")))

    prewindow_winner={}
    ambiguous_prewindow=set()
    for symbol, rows in by_symbol_prewindow.items():
        if len(rows)<=1:
            if rows:
                prewindow_winner[symbol]=rows[0][0]
            continue
        ranked=sorted(rows,key=lambda x:str(x[1] or ""),reverse=True)
        if len(ranked)>=2 and str(ranked[0][1] or "")==str(ranked[1][1] or ""):
            ambiguous_prewindow.add(symbol)
            continue
        prewindow_winner[symbol]=ranked[0][0]
        annotations.append({
            "symbol":symbol,
            "type":"PREWINDOW_CROSS_EXCHANGE_MIGRATION_RESOLUTION",
            "window_start":window_start,
            "active_exchange":ranked[0][0],
            "active_exchange_last_list":ranked[0][1],
            "suppressed_exchanges":[
                {"exchange":ex,"last_list":d} for ex,d in ranked[1:]
            ],
            "evidence":"LATEST_OFFICIAL_LIST_BEFORE_WINDOW_START",
        })

    for (symbol,exchange), arr in grouped.items():
        arr=sorted(
            arr,
            key=lambda x: (
                str(x.get("event_date")),
                0 if x.get("event_type")=="DELIST" else 1,
            ),
        )
        lists=[x for x in arr if x.get("event_type")=="LIST"]
        history_start=LISTING_HISTORY_START.get(exchange)

        listed=False
        for e in arr:
            d=str(e.get("event_date"))
            if d >= window_start:
                break
            if e.get("event_type")=="LIST":
                listed=True
            elif e.get("event_type")=="DELIST":
                listed=False

        if symbol in ambiguous_prewindow and listed:
            unresolved.append({
                "symbol":symbol,
                "exchange":exchange,
                "reason":"AMBIGUOUS_CROSS_EXCHANGE_MEMBERSHIP_AT_WINDOW_START",
                "window_start":window_start,
            })
            listed=False
        elif listed and prewindow_winner.get(symbol) and prewindow_winner[symbol] != exchange:
            listed=False

        current_start=window_start if listed else None
        future=[e for e in arr if str(e.get("event_date")) >= window_start]

        if (
            not listed
            and not lists
            and future
            and future[0].get("event_type")=="DELIST"
            and history_start
            and history_start < window_start
        ):
            listed=True
            current_start=window_start
            annotations.append({
                "symbol":symbol,
                "exchange":exchange,
                "type":"LEFT_CENSORED_AT_WINDOW_START",
                "window_start":window_start,
                "evidence_event":future[0],
                "note":"Actual listing date predates available official listing-history coverage; membership is asserted only from the governed research-window start.",
            })

        for e in future:
            d=str(e.get("event_date"))
            typ=e.get("event_type")
            if typ=="LIST":
                if listed:
                    annotations.append({
                        "symbol":symbol,
                        "exchange":exchange,
                        "type":"LIST_WHILE_ALREADY_LISTED",
                        "event":e,
                        "note":"Continuous membership; additional LIST is treated as reclassification, board change, or near-duplicate source record.",
                    })
                    continue
                listed=True
                current_start=d
            elif typ=="DELIST":
                if not listed:
                    unresolved.append({
                        "symbol":symbol,
                        "exchange":exchange,
                        "reason":"WINDOW_DELIST_WITHOUT_MEMBERSHIP",
                        "event":e,
                    })
                    continue
                intervals.append({
                    "symbol":symbol,
                    "exchange":exchange,
                    "name":str(e.get("name") or ""),
                    "listed_from":current_start,
                    "listed_to":d,
                    "source":"official_event_ledger_windowed",
                    "source_as_of":str(e.get("source_as_of") or ""),
                    "notes":"windowed_membership",
                })
                listed=False
                current_start=None

        if listed and current_start:
            name=""
            for e in reversed(arr):
                if e.get("name"):
                    name=str(e.get("name"))
                    break
            intervals.append({
                "symbol":symbol,
                "exchange":exchange,
                "name":name,
                "listed_from":current_start,
                "listed_to":None,
                "source":"official_event_ledger_windowed",
                "source_as_of":max(str(e.get("source_as_of") or "") for e in arr),
                "notes":"windowed_membership",
            })

    reconciled=reconcile_cross_exchange_migrations(intervals)
    for item in reconciled["migration_notes"]:
        annotations.append({"type":"CROSS_EXCHANGE_MIGRATION",**item})
    return {
        "intervals":sorted(reconciled["intervals"],key=lambda x:(x["exchange"],x["symbol"],x["listed_from"])),
        "unresolved":unresolved,
        "annotations":annotations,
        "window_start":window_start,
    }

def build_historical_universe_audit(
    *,
    official_payload: dict,
    current_universe: list[dict],
    audit_dates: list[str],
) -> dict:
    strict_intervals = list(official_payload.get("intervals") or [])
    strict_unresolved = list(official_payload.get("unresolved") or [])
    source_health = list(official_payload.get("health") or [])

    windowed = build_windowed_intervals(
        list(official_payload.get("events") or []),
        window_start=WINDOW_START,
    )
    intervals = list(windowed.get("intervals") or [])
    unresolved = list(windowed.get("unresolved") or [])
    validation = validate_intervals(intervals)

    current_by_exchange = defaultdict(set)
    for row in current_universe:
        symbol = str(row.get("symbol") or "")
        exchange = str(row.get("exchange") or "")
        if symbol and exchange:
            current_by_exchange[exchange].add(symbol)

    membership_by_exchange = defaultdict(set)
    membership_rows = list(official_payload.get("current_membership") or [])
    if membership_rows:
        for row in membership_rows:
            symbol=str(row.get("symbol") or "")
            exchange=str(row.get("exchange") or "")
            if symbol and exchange:
                membership_by_exchange[exchange].add(symbol)
    else:
        # Backward-compatible fallback for synthetic tests only.
        for exchange,symbols in current_by_exchange.items():
            membership_by_exchange[exchange].update(symbols)

    interval_by_exchange = defaultdict(set)
    for row in intervals:
        symbol = str(row.get("symbol") or "")
        exchange = str(row.get("exchange") or "")
        if symbol and exchange:
            interval_by_exchange[exchange].add(symbol)

    open_by_exchange = defaultdict(set)
    for row in intervals:
        if row.get("listed_to") in (None, ""):
            open_by_exchange[str(row.get("exchange") or "")].add(str(row.get("symbol") or ""))

    current_coverage = {}
    membership_alignment = {}
    exchanges=sorted(
        set(current_by_exchange)
        | set(membership_by_exchange)
        | set(interval_by_exchange)
        | set(open_by_exchange)
    )
    for exchange in exchanges:
        current = current_by_exchange.get(exchange, set())
        membership = membership_by_exchange.get(exchange, set())
        known = interval_by_exchange.get(exchange, set())
        open_now = open_by_exchange.get(exchange, set())

        # Quote/trade-active coverage is diagnostic only. Suspended securities
        # may legitimately remain listed while absent from current quote data.
        covered = current & known
        missing = sorted(current - known)
        current_coverage[exchange] = {
            "current_symbols": len(current),
            "symbols_with_listing_interval": len(covered),
            "coverage_pct": round((len(covered) / len(current) * 100.0), 4) if current else 0.0,
            "missing_current_symbols": missing[:200],
        }

        missing_open=sorted(membership-open_now)
        extraneous_open=sorted(open_now-membership)
        membership_alignment[exchange]={
            "current_membership_symbols":len(membership),
            "open_interval_symbols":len(open_now),
            "membership_open_coverage_pct":round(
                len(membership & open_now)/len(membership)*100.0,4
            ) if membership else 0.0,
            "missing_open_symbol_count":len(missing_open),
            "missing_open_symbols":missing_open[:200],
            "extraneous_open_symbol_count":len(extraneous_open),
            "extraneous_open_symbols":extraneous_open[:200],
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

    def _healthy(row: dict) -> bool:
        if "healthy" in row:
            return bool(row.get("healthy"))
        return bool(row.get("ok"))

    sources_ok = bool(source_health) and all(_healthy(x) for x in source_health)
    health_by_name = {str(x.get("source")): x for x in source_health}
    historical_source_coverage_ok = all(
        name in health_by_name
        and _healthy(health_by_name[name])
        and int(health_by_name[name].get("parsed_events") or 0) > 0
        for name in REQUIRED_HISTORICAL_SOURCES
    )
    current_coverage_ok = all(
        x["coverage_pct"] >= MIN_CURRENT_INTERVAL_COVERAGE_PCT
        for x in current_coverage.values()
        if x["current_symbols"] > 0
    )
    open_interval_alignment_ok = all(
        int(x.get("extraneous_open_symbol_count") or 0) == 0
        and int(x.get("missing_open_symbol_count") or 0) == 0
        for x in membership_alignment.values()
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
        and open_interval_alignment_ok
        and unresolved_ok
        and historical_dates_nonempty
    )

    # Diagnostic timelines for unresolved delists and overlapping intervals.
    event_rows = list(official_payload.get("events") or [])
    unresolved_samples = unresolved[:200]
    diagnostic_symbols = {
        (str(x.get("symbol") or ""), str(x.get("exchange") or ""))
        for x in unresolved_samples
    }
    for err in validation.get("errors") or []:
        if str(err).startswith("overlap:"):
            _, symbol, exchange = str(err).split(":", 2)
            diagnostic_symbols.add((symbol, exchange))
    for exchange, x in membership_alignment.items():
        for symbol in x.get("extraneous_open_symbols") or []:
            diagnostic_symbols.add((str(symbol), str(exchange)))
        for symbol in x.get("missing_open_symbols") or []:
            diagnostic_symbols.add((str(symbol), str(exchange)))

    timelines = {}
    for symbol, exchange in sorted(diagnostic_symbols):
        key = f"{exchange}:{symbol}"
        timelines[key] = sorted(
            [
                {
                    "event_type": x.get("event_type"),
                    "event_date": x.get("event_date"),
                    "source": x.get("source"),
                    "source_url": x.get("source_url"),
                    "name": x.get("name"),
                    "notes": x.get("notes"),
                }
                for x in event_rows
                if str(x.get("symbol") or "") == symbol
                and str(x.get("exchange") or "") == exchange
            ],
            key=lambda x: (str(x.get("event_date") or ""), str(x.get("event_type") or "")),
        )

    unresolved_by_exchange = defaultdict(int)
    for x in unresolved:
        unresolved_by_exchange[str(x.get("exchange") or (x.get("event") or {}).get("exchange") or "")] += 1

    return {
        "schema_version": "1.0",
        "source_health": source_health,
        "events": len(official_payload.get("events") or []),
        "strict_intervals": len(strict_intervals),
        "strict_unresolved": len(strict_unresolved),
        "window_start": WINDOW_START,
        "intervals": len(intervals),
        "unresolved": len(unresolved),
        "window_annotations": len(windowed.get("annotations") or []),
        "left_censored_count": sum(
            1 for x in (windowed.get("annotations") or [])
            if x.get("type")=="LEFT_CENSORED_AT_WINDOW_START"
        ),
        "continuous_listing_annotations": sum(
            1 for x in (windowed.get("annotations") or [])
            if x.get("type")=="LIST_WHILE_ALREADY_LISTED"
        ),
        "unresolved_by_exchange": dict(sorted(unresolved_by_exchange.items())),
        "unresolved_samples": unresolved_samples,
        "diagnostic_event_timelines": timelines,
        "interval_validation": validation,
        "current_interval_coverage": current_coverage,
        "current_membership_alignment": membership_alignment,
        "historical_dates": dates,
        "historical_source_coverage_ok": historical_source_coverage_ok,
        "current_open_interval_alignment_ok": open_interval_alignment_ok,
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
            "window_start": WINDOW_START,
            "strict_pre_window_unresolved_do_not_block_window_gate": True,
            "current_open_intervals_must_match_official_listing_membership": True,
            "quote_universe_is_diagnostic_not_membership": True,
            "managed_stocks_are_excluded_from_tpex_mainboard_membership": True,
            "extraneous_open_intervals_allowed": 0,
            "missing_open_intervals_allowed": 0,
            "window_unresolved_events_allowed": 0,
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
        f"- Strict intervals: {report['strict_intervals']:,}",
        f"- Strict unresolved (full history): {report['strict_unresolved']:,}",
        f"- Research window start: {report['window_start']}",
        f"- Windowed intervals: {report['intervals']:,}",
        f"- Window unresolved: {report['unresolved']:,}",
        f"- Left-censored at window start: {report['left_censored_count']:,}",
        f"- Continuous-listing annotations: {report['continuous_listing_annotations']:,}",
        f"- Unresolved by exchange: {report.get('unresolved_by_exchange', {})}",
        f"- Interval validation: {'PASS' if report['interval_validation']['valid'] else 'FAIL'}",
        f"- Historical source coverage: {'PASS' if report['historical_source_coverage_ok'] else 'FAIL'}",
        f"- Historical dates non-empty: {'PASS' if report['historical_dates_nonempty'] else 'FAIL'}",
        f"- Current open-interval alignment: {'PASS' if report.get('current_open_interval_alignment_ok') else 'FAIL'}",
        f"- Historical Universe Gate: {'PASS' if report['historical_universe_gate_pass'] else 'FAIL'}",
        "",
        "## Current-universe interval coverage",
        "",
        "| Exchange | Current | Covered by interval | Coverage | Open intervals | Extraneous open |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for exchange, x in report["current_interval_coverage"].items():
        lines.append(
            f"| {exchange} | {x['current_symbols']:,} | "
            f"{x['symbols_with_listing_interval']:,} | {x['coverage_pct']:.4f}% | "
            f"{x.get('open_interval_symbols',0):,} | {x.get('extraneous_open_symbol_count',0):,} |"
        )

    lines += [
        "",
        "## Current listing-membership alignment",
        "",
        "| Exchange | Official membership | Open intervals | Membership coverage | Missing open | Extraneous open |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for exchange,x in report.get("current_membership_alignment",{}).items():
        lines.append(
            f"| {exchange} | {x['current_membership_symbols']:,} | "
            f"{x['open_interval_symbols']:,} | {x['membership_open_coverage_pct']:.4f}% | "
            f"{x['missing_open_symbol_count']:,} | {x['extraneous_open_symbol_count']:,} |"
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

    # Persist the canonical governed-window membership intervals as a first-class
    # artifact. Downstream research (including W1 Swing) must consume these
    # intervals instead of reconstructing historical membership from today's
    # listing universe.
    windowed = build_windowed_intervals(
        list(official.get("events") or []),
        window_start=WINDOW_START,
    )
    pit_snapshot = {
        "schema_version": "1.0",
        "window_start": WINDOW_START,
        "source_as_of": official.get("source_as_of"),
        "historical_universe_gate_pass": report.get("historical_universe_gate_pass"),
        "interval_validation": report.get("interval_validation"),
        "intervals": windowed.get("intervals") or [],
        "annotations": windowed.get("annotations") or [],
        "unresolved": windowed.get("unresolved") or [],
    }
    (out / "pit_intervals.json").write_text(
        json.dumps(pit_snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_markdown(report, out / "audit.md")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
