"""Fail-closed intraday quote-coverage quality gate.

Operational MIS OTC may be used as an explicitly labeled fallback but must
never be described as an official TPEx-certified full-market feed.
This module does not alter P0-C ranking or Production strategy semantics.
"""
from __future__ import annotations


class MarketCoverageError(RuntimeError):
    """A scanner output is not eligible for trading-signal publication."""


def validate_operational_quote_coverage(scan: dict) -> dict:
    universe = int(scan.get("universe_count") or 0)
    covered = int(scan.get("mis_quote_count") or 0)
    pct = float(scan.get("quote_coverage_pct") or 0)
    official = (scan.get("source_health") or {}).get("official_universe") or {}
    twse = (scan.get("source_health") or {}).get("twse_intraday") or {}
    tpex = (scan.get("source_health") or {}).get("tpex_intraday") or {}
    checks = {
        "official_twse_universe": int(official.get("twse") or 0) >= 500,
        "official_tpex_universe": int(official.get("tpex") or 0) >= 400,
        "mis_twse_valid_last_trade": int(twse.get("count") or 0) >= 400,
        "mis_otc_valid_last_trade": int(tpex.get("fallback_count") or 0) >= 300,
        "operational_coverage_at_least_70pct": pct >= 70.0,
        "scanner_operational_flag": scan.get("operational_full_market_scan") is True,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "BLOCKED_QUOTE_COVERAGE",
        "checks": checks,
        "universe_count": universe,
        "valid_trade_quote_count": covered,
        "coverage_pct": pct,
        "market_scope": "TWSE_MIS_TSE_AND_OTC_OPERATIONAL_ONLY",
        "tpex_official_intraday_certified": False,
        "trading_signal_publication_allowed": all(checks.values()),
        "missing_valid_last_trade_count": max(universe - covered, 0),
        "reason": (
            "Quotes with unavailable last-traded price are missing; "
            "do not replace with prior close, open, high, low, bid or ask."
        ),
    }
    return result


def require_operational_quote_coverage(scan: dict) -> dict:
    result = validate_operational_quote_coverage(scan)
    if result["status"] != "PASS":
        raise MarketCoverageError(
            "BLOCKED_QUOTE_COVERAGE: "
            f"{result['valid_trade_quote_count']}/{result['universe_count']} "
            f"({result['coverage_pct']:.2f}%) valid last-trade prices. "
            "No candidate publication or normal Telegram signal."
        )
    return result
