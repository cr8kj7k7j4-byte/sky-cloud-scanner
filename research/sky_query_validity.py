"""Canonical all-market information-query validity; NEVER approves executed quotes.

The shared classification applies to both intraday and postmarket *information*
reports, not trade gates.  Explicit numeric zero volume + no price is a
successful query only after a valid provider response and source-date match.
"""
from __future__ import annotations

from datetime import date, datetime
from math import isfinite


def _source_date(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def query_status(row: dict, report: dict, *, mode: str) -> str:
    """Separate query completeness from observed price and execution validity."""
    market = row.get("exchange")
    metadata = (report.get("snapshot_integrity") or {}).get(market) or {}
    source_date = _source_date(metadata.get("snapshot_date"))
    try:
        checked = datetime.fromisoformat(report.get("checked_at_tpe", "")).date()
    except (TypeError, ValueError):
        checked = None
    if (
        market not in ("TWSE", "TPEx")
        or (report.get("snapshot_status") or {}).get(market) != "RETURNED"
        or metadata.get("api_response_valid") is not True
        or row.get("source") != "Fugle paid bulk snapshot"
        or row.get("snapshot_is_trial") is not False
        or source_date is None or checked is None
        or row.get("snapshot_source_date") != source_date.isoformat()
        or source_date > checked
        or (mode == "INTRADAY_INFORMATION" and source_date != checked)
    ):
        return "HOLD_UNVERIFIED_INFORMATION_QUERY"
    price = row.get("last_price")
    if type(price) in (int, float) and isfinite(price) and price > 0:
        return "VALID_QUERY_WITH_OBSERVED_PRICE"
    volume = row.get("volume")
    if price is None and type(volume) in (int, float) and isfinite(volume) and volume == 0:
        return "VALID_QUERY_ZERO_REPORTED_VOLUME_NO_PRICE"
    return "HOLD_UNVERIFIED_INFORMATION_QUERY"


def apply_query_validity(report: dict, *, mode: str) -> dict:
    """Apply full-universe observation status without changing trading gates."""
    if mode not in ("INTRADAY_INFORMATION", "POSTMARKET_RESEARCH_ONLY"):
        raise ValueError("INVALID_INFORMATION_QUERY_MODE")
    rows = report.get("all_symbols") or []
    counts = {"price": 0, "zero_volume_no_price": 0, "hold": 0}
    market_counts = {
        market: {"valid_queries": 0, "zero_volume_no_price": 0, "hold": 0}
        for market in ("TWSE", "TPEx")
    }
    lookup = {}
    for row in rows:
        if not isinstance(row, dict):
            counts["hold"] += 1
            continue
        status = query_status(row, report, mode=mode)
        row["information_query_status"] = status
        row["information_query_valid"] = status.startswith("VALID_QUERY_")
        row["information_observed_price_valid"] = status == "VALID_QUERY_WITH_OBSERVED_PRICE"
        # This contract makes NO assertion about real executed trades or A2.
        row["information_executed_trade_certified_by_query"] = False
        row["information_query_trading_eligible"] = False
        row["trade_signal"] = False
        row["production_eligible"] = False
        bucket = (
            "price" if status == "VALID_QUERY_WITH_OBSERVED_PRICE"
            else "zero_volume_no_price" if status == "VALID_QUERY_ZERO_REPORTED_VOLUME_NO_PRICE"
            else "hold"
        )
        counts[bucket] += 1
        if row.get("exchange") in market_counts:
            m = market_counts[row["exchange"]]
            if bucket == "hold":
                m["hold"] += 1
            else:
                m["valid_queries"] += 1
                if bucket == "zero_volume_no_price":
                    m["zero_volume_no_price"] += 1
        lookup[(row.get("exchange"), row.get("symbol"))] = row

    for detail in report.get("missing_price_diagnostics") or []:
        if isinstance(detail, dict):
            matched = lookup.get((detail.get("exchange"), detail.get("symbol"))) or {}
            detail["information_query_status"] = matched.get(
                "information_query_status", "HOLD_UNVERIFIED_INFORMATION_QUERY"
            )
            detail["information_query_valid"] = (
                detail["information_query_status"] == "VALID_QUERY_ZERO_REPORTED_VOLUME_NO_PRICE"
                and type(detail.get("reported_volume")) in (int, float)
                and isfinite(detail["reported_volume"])
                and detail["reported_volume"] == 0
            )
            detail["information_price_valid"] = False

    official = report.get("official_universe_count_before_research_exclusion")
    if type(official) is not int or official < len(rows):
        official = len(rows)
    total = sum(counts.values())
    valid = counts["price"] + counts["zero_volume_no_price"]
    report["information_query_mode"] = mode
    report["information_query_with_price_count"] = counts["price"]
    report["information_query_zero_volume_no_price_count"] = counts["zero_volume_no_price"]
    report["information_query_valid_count"] = valid
    report["information_query_hold_count"] = counts["hold"]
    report["information_query_market_counts"] = market_counts
    report["information_query_official_denominator"] = official
    report["information_query_valid_pct_official"] = (
        round(100 * valid / official, 2) if official else None
    )
    report["information_query_full_universe_complete"] = (
        official > 0 and len(rows) == official and total == official and valid == official
        and all((report.get("snapshot_status") or {}).get(m) == "RETURNED"
                for m in ("TWSE", "TPEx"))
    )
    report["information_query_provenance_note"] = (
        "Provider-reported zero volume with no observed price counts as a "
        "completed information query only. It does not prove an exchange halt, "
        "absence of every transaction, an executable price or A2 execution."
    )
    return report
