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
    # Fugle can supply ISO 8601 execution timestamps as well as epoch values.
    # Never interpret a timezone-naive string as a Taiwanese last trade.
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if parsed.utcoffset() is not None:
                return parsed.astimezone(TPE)
        except ValueError:
            pass
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


def mis_executed_trade_row(row, now=None, *, max_age_seconds=180):
    """Validate a fresh MIS executed quote using exchange date + local trade time.

    A bare HH:MM:SS without an exchange-supplied date cannot certify a trade
    on the current session. This affects candidate execution, not historical PIT.
    """
    now = now or datetime.now(TPE)
    try:
        price = float(row.get("last"))
        if price <= 0:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        return False
    raw_date = str(row.get("quote_date") or "").strip().replace("-", "").replace("/", "")
    if raw_date != now.strftime("%Y%m%d"):
        return False
    raw_time = str(row.get("quote_time") or "").strip()
    try:
        trade_time = datetime.strptime(raw_time, "%H:%M:%S").time()
        dt = datetime.combine(now.date(), trade_time, tzinfo=TPE)
    except ValueError:
        return False
    age = (now - dt).total_seconds()
    return -30 <= age <= max_age_seconds


def validate_whole_market_rows(universe, rows, now=None, *, min_coverage_pct=80.0,
                               min_exchange_pct=70.0, max_age_seconds=180):
    """Evaluate real executed-quote coverage independently for TSE and OTC.

    This checks operational *executed trade* validity only. It does not grant
    TPEx-official certification to MIS OTC or change strategy eligibility.
    No stale daily prices, quotes with missing trade time, or synthetic last.
    """
    now = now or datetime.now(TPE)
    by_symbol = {str(x.get("symbol")): x for x in universe}
    target = {
        "TWSE": sum(x.get("exchange") == "TWSE" for x in universe),
        "TPEx": sum(x.get("exchange") == "TPEx" for x in universe),
    }
    accepted = {}
    snapshot_reference = {}
    rejection = {}
    for row in rows:
        symbol = str(row.get("symbol") or "")
        meta = by_symbol.get(symbol)
        if not meta or meta.get("exchange") not in target:
            rejection["NOT_IN_OFFICIAL_UNIVERSE"] = rejection.get("NOT_IN_OFFICIAL_UNIVERSE", 0) + 1
            continue
        # A bulk snapshot is acceptable only when it explicitly carries a
        # verified last-executed timestamp, not the snapshot download time.
        if row.get("quote_source") == "Fugle bulk snapshot":
            # Snapshot reference coverage does NOT require lastTrade.time.
            # It is deliberately separate from verified executed-trade coverage.
            try:
                reference_price = float(row.get("last"))
            except (ValueError, TypeError):
                reference_price = 0.0
            if (reference_price > 0 and str(row.get("quote_date") or "") == now.date().isoformat()
                    and row.get("isTrial") is not True):
                snapshot_reference[symbol] = row
            ts = timestamp_tpe(row.get("last_trade_timestamp"))
            try:
                price = float(row.get("last"))
            except (ValueError, TypeError):
                price = 0.0
            age = (now - ts).total_seconds() if ts else None
            valid = (
                price > 0 and ts is not None
                and str(row.get("quote_date") or "") == now.date().isoformat()
                and ts.date() == now.date()
                and age is not None and -30 <= age <= max_age_seconds
            )
        elif row.get("quote_source") == "TWSE MIS":
            valid = mis_executed_trade_row(row, now, max_age_seconds=max_age_seconds)
        else:
            valid = False
        if valid:
            accepted[symbol] = row
        else:
            rejection["STALE_OR_UNVERIFIED_EXECUTED_TRADE"] = rejection.get(
                "STALE_OR_UNVERIFIED_EXECUTED_TRADE", 0
            ) + 1

    counts = {
        k: sum(by_symbol[s].get("exchange") == k for s in accepted)
        for k in target
    }
    rates = {
        k: round(100 * counts[k] / target[k], 2) if target[k] else 0.0
        for k in target
    }
    total = len(by_symbol)
    coverage = round(100 * len(accepted) / total, 2) if total else 0.0
    passed = bool(
        total and all(target[k] > 0 and rates[k] >= min_exchange_pct for k in target)
        and coverage >= min_coverage_pct
    )
    return {
        "status": "PASS_VALID_EXECUTED_LIVE" if passed else "BLOCKED_EXTERNAL_DATA",
        "valid_whole_market_operational": passed,
        "universe_count": total,
        "valid_quote_count": len(accepted),
        "snapshot_reference_count": len(snapshot_reference),
        "snapshot_reference_coverage_pct": round(100 * len(snapshot_reference) / total, 2) if total else 0.0,
        "snapshot_reference_requires_last_trade_time": False,
        "quote_coverage_pct": coverage,
        "by_exchange": {
            k: {"universe": target[k], "valid": counts[k], "coverage_pct": rates[k]}
            for k in target
        },
        "rejected": rejection,
        "data_time": now.isoformat(),
        "quote_scope": "WHOLE_MARKET_EXECUTED_LIVE" if passed else "PARTIAL_EXECUTED_LIVE",
        "otc_mis_is_official_tpex_live": False,
        "accepted_rows": list(accepted.values()),
    }
