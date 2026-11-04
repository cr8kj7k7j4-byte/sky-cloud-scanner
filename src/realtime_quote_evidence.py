"""Read-only, fail-closed Taiwan quote provenance for Sky current-state commands.

A candidate's verified trade is not whole-market coverage. EOD prices,
reference prices, closePrice and order-book prices never substitute for a
confirmed same-day executed trade.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")


def timestamp_tpe(value):
    """Normalize an actual trade timestamp to Asia/Taipei; reject missing time."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
        if number > 1e14:
            number /= 1_000_000
        elif number > 1e11:
            number /= 1_000
        return datetime.fromtimestamp(number, TPE)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def fugle_executed_trade(quote, now=None, *, max_age_seconds=120):
    """Return a verified trade evidence tuple (price, trade_time, status).

    Only lastTrade.price or lastPrice are eligible prices. closePrice is
    deliberately excluded: it may represent a prior or closing value.
    The timestamp must describe the last execution, not just quote refresh.
    """
    now = now or datetime.now(TPE)
    if not isinstance(quote, dict):
        return None, None, "INVALID_PAYLOAD"
    trade = quote.get("lastTrade")
    trade = trade if isinstance(trade, dict) else {}
    raw = trade.get("price")
    if raw is None:
        raw = quote.get("lastPrice")
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return None, None, "MISSING_EXECUTED_LAST_PRICE"
    ts = timestamp_tpe(trade.get("time") or quote.get("closeTime"))
    if ts is None:
        return None, None, "MISSING_EXECUTED_TRADE_TIME"
    if quote.get("date") != now.date().isoformat() or ts.date() != now.date():
        return None, ts, "STALE_TRADING_DATE"
    age = (now - ts).total_seconds()
    if age < -30:
        return None, ts, "FUTURE_TRADE_TIMESTAMP"
    if age > max_age_seconds:
        return None, ts, "STALE_EXECUTED_TRADE"
    if quote.get("isTrial") is True:
        return None, ts, "TRIAL_QUOTE"
    return price, ts, "FRESH_EXECUTED_TRADE"


def market_scope(report):
    """Classify evidence scope without ever upgrading a candidate sample.

    Legacy 'operational_full_market_scan' may mean broad daily signal universe
    (not realtime). Only explicit certified executed-quote scope is live-market.
    """
    if report.get("strict_official_full_market_certified") is True and report.get("quote_scope") == "WHOLE_MARKET_EXECUTED_LIVE":
        return "WHOLE_MARKET_REALTIME_CERTIFIED"
    if report.get("live_whole_market_certified") is True and report.get("quote_scope") == "WHOLE_MARKET_EXECUTED_LIVE":
        return "WHOLE_MARKET_REALTIME_OPERATIONAL"
    if report.get("quote_scope") in ("FROZEN_SIGNAL_CANDIDATES_ONLY", "CANDIDATES_ONLY") or report.get("live_quote_scope") == "CANDIDATES_ONLY":
        return "CANDIDATES_ONLY_REALTIME"
    if report.get("daily_scope_status") == "PASS_DAILY_CROSS_SECTION":
        return "OFFICIAL_DAILY_CROSS_SECTION"
    return "BLOCKED_OR_UNVERIFIED"
