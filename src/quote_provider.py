"""Fugle-first market evidence, with MIS used only as an explicitly labelled fallback.

This module does not certify an official TPEx realtime feed or authorize trades.
"""
from .official import fetch_fugle_snapshot_quotes, fetch_mis_quotes
from .realtime_quote_evidence import validate_whole_market_rows


def collect_market_quotes(universe, *, now, fugle_fetch=None, mis_fetch=None,
                          min_coverage_pct=80.0, min_exchange_pct=70.0):
    fugle_fetch = fugle_fetch or fetch_fugle_snapshot_quotes
    mis_fetch = mis_fetch or fetch_mis_quotes
    try:
        provider_rows, warnings = fugle_fetch(universe, trading_date=now.date().isoformat())
    except Exception as exc:
        provider_rows, warnings = [], [f"FUGLE_PRIMARY_ERROR: {type(exc).__name__}"]
    primary = validate_whole_market_rows(
        universe, provider_rows, now=now,
        min_coverage_pct=min_coverage_pct, min_exchange_pct=min_exchange_pct,
    )
    if primary["valid_whole_market_operational"]:
        return {
            "rows": primary["accepted_rows"], "warnings": warnings,
            "audit": primary, "provider": "Fugle bulk snapshot",
            "primary_status": "PASS_VALID_EXECUTED_LIVE",
            "fallback_used": False, "official_tpex_realtime_certified": False,
        }

    # Never mix provider and fallback rows to manufacture coverage.
    # Preserve the primary failure in evidence even if MIS independently passes.
    try:
        fallback_rows, fallback_warnings = mis_fetch(universe)
    except Exception as exc:
        fallback_rows, fallback_warnings = [], [f"MIS_FALLBACK_ERROR: {type(exc).__name__}"]
    fallback = validate_whole_market_rows(
        universe, fallback_rows, now=now,
        min_coverage_pct=min_coverage_pct, min_exchange_pct=min_exchange_pct,
    )
    return {
        "rows": fallback["accepted_rows"],
        "warnings": list(warnings) + ["FUGLE_PRIMARY_INSUFFICIENT_EXECUTED_COVERAGE"] + list(fallback_warnings),
        "audit": fallback, "provider": "TWSE MIS (fallback, OTC not TPEx-certified)",
        "primary_status": primary["status"],
        "primary_quote_coverage_pct": primary["quote_coverage_pct"],
        "fallback_used": True, "official_tpex_realtime_certified": False,
    }
