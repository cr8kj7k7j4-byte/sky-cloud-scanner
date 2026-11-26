"""Pure adapter for already-fetched Fugle individual quotes in SKY維持率.

No HTTP, no credentials, no paid calls. Strict raw lastTrade evidence is required.
Raw response provenance/entitlement MUST be independently verified upstream.
This adapter never grants trade eligibility or certifies a whole-market scan.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from src.realtime_quote_evidence import TPE, timestamp_tpe

SOURCE = "Fugle individual quote /intraday/quote (caller-supplied)"


def margin_row_with_a2_quote(
    row: Mapping[str, Any], quote: Mapping[str, Any], *,
    observed_at: datetime, max_age_seconds: int = 120,
) -> dict[str, Any]:
    """Attach a validated lastTrade.price/time/serial to a research input row.

    Does not authenticate the HTTP origin. Caller must establish that separately.
    Returns structured HOLD on failure instead of copying an A1/lastPrice fallback.
    """
    result = dict(row)
    for key in ("last_trade_price_twd", "price_source", "price_date",
                "price_evidence", "price_trade_time_tpe",
                "price_trade_serial"):
        result.pop(key, None)
    result["price_quote_validation"] = "HOLD_A2_RAW_TRADE_NOT_VERIFIED"
    result["price_evidence"] = "UNVERIFIED"
    result["a2_origin_independently_verified"] = False
    result["buy_eligible"] = False
    result["trade_status"] = "NO_TRADE"
    if not isinstance(observed_at, datetime) or observed_at.utcoffset() is None:
        result["price_reject_reason"] = "INVALID_OBSERVATION_TIME"
        return result
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or not 1 <= max_age_seconds <= 180:
        result["price_reject_reason"] = "INVALID_MAX_AGE"
        return result
    now = observed_at.astimezone(TPE)
    if not isinstance(quote, Mapping) or quote.get("isTrial") is True:
        result["price_reject_reason"] = "INVALID_OR_TRIAL_QUOTE"
        return result
    if quote.get("date") != now.date().isoformat():
        result["price_reject_reason"] = "QUOTE_DATE_MISMATCH"
        return result
    trade = quote.get("lastTrade")
    if not isinstance(trade, Mapping):
        result["price_reject_reason"] = "MISSING_LAST_TRADE"
        return result
    serial = trade.get("serial")
    if isinstance(serial, bool) or not isinstance(serial, int) or serial <= 0:
        result["price_reject_reason"] = "MISSING_TRADE_SERIAL"
        return result
    raw_price = trade.get("price")
    try:
        if isinstance(raw_price, bool):
            raise ValueError()
        price = Decimal(str(raw_price))
        if not price.is_finite() or price <= 0:
            raise ValueError()
    except (TypeError, InvalidOperation, ValueError):
        result["price_reject_reason"] = "MISSING_EXECUTED_TRADE_PRICE"
        return result
    trade_at = timestamp_tpe(trade.get("time"))
    if trade_at is None or trade_at.date() != now.date():
        result["price_reject_reason"] = "INVALID_LAST_TRADE_TIME"
        return result
    age = (now - trade_at).total_seconds()
    if not -30 <= age <= max_age_seconds:
        result["price_reject_reason"] = "STALE_OR_FUTURE_TRADE"
        return result
    if str(row.get("symbol") or "") != str(quote.get("symbol") or ""):
        result["price_reject_reason"] = "QUOTE_SYMBOL_MISMATCH"
        return result
    result.update({
        "last_trade_price_twd": str(price),
        "price_source": SOURCE,
        "price_date": now.date().isoformat(),
        "price_evidence": "EXECUTED_TRADE",
        "price_trade_time_tpe": trade_at.isoformat(),
        "price_trade_serial": serial,
        "price_quote_validation": "A2_FIELDS_CHECKED_CALLER_SOURCE_UNVERIFIED",
    })
    result.pop("price_reject_reason", None)
    return result
