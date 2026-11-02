"""Quote freshness validation for Sky reports (research integration gate).

No provider is assumed official just because a quote has a price.
Consumers must supply a verifiable provider timestamp / trading date.
This module does not modify Production selection or execution.
"""
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")


def validate_quote_timestamp(*, quote_time, trade_date=None, now=None, max_age_seconds=180):
    """Return machine-readable fail-closed status for one quoted value.

    Accept an ISO 8601 offset-aware instant, or a time-of-day tied to an
    explicitly supplied YYYY-MM-DD trading date. Never infer trade date
    from the current date, as that would mislabel stale snapshots.
    """
    now = now or datetime.now(TZ)
    if now.tzinfo is None:
        return {"ok": False, "status": "INVALID_NOW"}
    if not quote_time:
        return {"ok": False, "status": "MISSING_QUOTE_TIMESTAMP"}
    try:
        if isinstance(quote_time, datetime):
            timestamp = quote_time
        elif isinstance(quote_time, str) and ("T" in quote_time or " " in quote_time):
            timestamp = datetime.fromisoformat(quote_time.replace("Z", "+00:00"))
        else:
            if not trade_date:
                return {"ok": False, "status": "MISSING_TRADE_DATE"}
            d = date.fromisoformat(str(trade_date))
            t = time.fromisoformat(str(quote_time))
            timestamp = datetime.combine(d, t, tzinfo=TZ)
        if timestamp.tzinfo is None:
            return {"ok": False, "status": "AMBIGUOUS_TIMEZONE"}
        delta = (now.astimezone(TZ) - timestamp.astimezone(TZ)).total_seconds()
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "INVALID_QUOTE_TIMESTAMP"}
    if delta < -30:
        return {"ok": False, "status": "FUTURE_QUOTE_TIMESTAMP", "age_seconds": round(delta, 2)}
    if delta > max_age_seconds:
        return {"ok": False, "status": "STALE_QUOTE", "age_seconds": round(delta, 2)}
    return {"ok": True, "status": "PASS", "age_seconds": round(max(delta, 0), 2)}


def validate_coverage(*, valid_quotes, universe_count, min_ratio=0.70):
    """Trading universe coverage must be known and pass explicit threshold."""
    if universe_count <= 0 or valid_quotes < 0:
        return {"ok": False, "status": "INVALID_COVERAGE"}
    ratio = valid_quotes / universe_count
    return {"ok": ratio >= min_ratio, "status": "PASS" if ratio >= min_ratio else "INSUFFICIENT_COVERAGE", "coverage_pct": round(ratio * 100, 2)}
