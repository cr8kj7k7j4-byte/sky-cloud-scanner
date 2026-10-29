"""Fail-closed validation for Fugle intraday quote observations.

This is a pure data-quality layer; it does not create a trading signal.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")


def validate_fugle_quote(quote: dict, symbol: str, *, now: datetime | None = None,
                         max_age_seconds: int = 120) -> dict:
    """Return normalized metadata; raise ValueError when a current trade quote is unsafe.

    `lastUpdated` is Fugle's epoch microseconds. A closing quote may be valid
    historical evidence but is never passed off as a live intraday quote.
    """
    if not isinstance(quote, dict):
        raise ValueError("FUGLE_QUOTE_NOT_OBJECT")
    if str(quote.get("symbol", "")) != str(symbol):
        raise ValueError("FUGLE_SYMBOL_MISMATCH")
    raw = quote.get("lastUpdated")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw <= 0:
        raise ValueError("FUGLE_TIMESTAMP_MISSING")
    stamp = datetime.fromtimestamp(raw / 1_000_000, tz=TAIPEI)
    current = now or datetime.now(TAIPEI)
    if current.tzinfo is None:
        raise ValueError("NOW_MUST_BE_TIMEZONE_AWARE")
    current = current.astimezone(TAIPEI)
    age = (current - stamp).total_seconds()
    if age < -30:
        raise ValueError("FUGLE_FUTURE_TIMESTAMP")
    price = quote.get("lastPrice")
    if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
        raise ValueError("FUGLE_PRICE_MISSING")
    if quote.get("isClose") is True:
        raise ValueError("FUGLE_MARKET_CLOSED")
    if age > max_age_seconds:
        raise ValueError("FUGLE_QUOTE_STALE")
    if current.weekday() >= 5 or not (current.replace(hour=9, minute=0, second=0, microsecond=0)
                                       <= current <= current.replace(hour=13, minute=30, second=0, microsecond=0)):
        raise ValueError("OUTSIDE_REGULAR_MARKET_SESSION")
    return {"source": "Fugle", "symbol": str(symbol), "price": float(price),
            "observed_at": stamp.isoformat(), "age_seconds": age, "status": "LIVE_QUOTE_VALID"}
