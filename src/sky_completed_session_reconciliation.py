"""W0 #363: completed-session Fugle same-source quote/trades/5m arithmetic.

This uses an already downloaded same-run source report. It is NOT A2 current
freshness, cross-exchange reconciliation, atomic PIT, independent VWAP, or a
trading signal. Never calls any provider, creates orders or guesses prices.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone, time as clocktime

TPE = timezone(timedelta(hours=8))
HISTORY_PASS = "PASS_COMPLETED_HISTORICAL_5M_RESEARCH_ONLY"
PASS_TRADE = "PASS_PRIOR_SESSION_LAST_TRADE_SAME_SOURCE_RESEARCH_ONLY"
PASS_VOLUME = "PASS_FUGLE_SAME_SOURCE_TRADES_QUOTE_5M_VOLUME_RECONCILED"
PASS_MEAN = "PASS_FUGLE_TRADES_WEIGHTED_MEAN_RESEARCH_ONLY"
HOLD = "HOLD_PRIOR_SESSION_SOURCE_RECONCILIATION"


def _real(x):
    return type(x) in (int, float) and math.isfinite(x) and x > 0


def _local_micros(value):
    if type(value) is not int or value <= 0:
        raise ValueError("INVALID_TRADE_TIMESTAMP")
    try:
        return datetime.fromtimestamp(value / 1_000_000, tz=TPE)
    except (OverflowError, ValueError, OSError) as exc:
        raise ValueError("INVALID_TRADE_TIMESTAMP") from exc


def reconcile(audit: dict, *, observed_at=None) -> dict:
    """All quantities are *same Fugle source*, completed session only."""
    now = observed_at or datetime.now(TPE)
    out = {
        "schema": "SKY_FUGLE_PRIOR_SESSION_ARITHMETIC_V1",
        "status": HOLD, "reason": "INSUFFICIENT_PRIOR_SESSION_PROVENANCE",
        "last_trade_status": "HOLD",
        "volume_status": "HOLD",
        "weighted_mean_status": "HOLD",
        "source_date": None, "page_terminal_verified": False,
        "independent_vwap_certified": False,
        "cross_source_volume_certified": False,
        "atomic_pit_certified": False,
        "current_session_trade_freshness_certified": False,
        "execution_authorized": False, "production_eligible": False,
        "automatic_order": False,
        "trade_action": "禁止交易",
    }
    if not isinstance(audit, dict):
        return out
    quote = audit.get("quote_raw")
    history = audit.get("historical_5m_research")
    pages = audit.get("trades_raw_pages")
    symbol = audit.get("symbol")
    if not (isinstance(quote, dict) and isinstance(history, dict)
            and isinstance(pages, list) and pages
            and isinstance(symbol, str) and symbol.isascii() and symbol.isdigit()
            and quote.get("symbol") == symbol and history.get("symbol") == symbol
            and history.get("status") == HISTORY_PASS
            and history.get("reused_no_new_fugle_http") is True
            and isinstance(history.get("source_run_id"), str)
            and isinstance(history.get("source_json_sha256"), str)
            and len(history["source_json_sha256"]) == 64):
        return out
    session = history.get("source_date")
    try:
        source_day = datetime.strptime(session, "%Y-%m-%d").date()
        if (source_day >= now.astimezone(TPE).date() or quote.get("date") != session
                or history.get("volume_raw_unit") != "lots"):
            raise ValueError("SESSION_IDENTITY")
    except (TypeError, ValueError):
        out["reason"] = "HOLD_SOURCE_DATE_MISMATCH_OR_NOT_COMPLETED"
        return out
    out["source_date"] = session
    raw = []
    for i, page in enumerate(pages):
        if not isinstance(page, dict) or page.get("offset") != 500*i:
            out["reason"] = "HOLD_PAGINATION_OFFSET_MISMATCH"
            return out
        data = page.get("data")
        if not isinstance(data, list):
            out["reason"] = "HOLD_PAGINATION_NOT_LIST"
            return out
        if not data:
            if i != len(pages)-1:
                out["reason"] = "HOLD_PAGINATION_PREMATURE_EMPTY_PAGE"
                return out
            out["page_terminal_verified"] = True
        else:
            # Fugle may return fewer than limit=500 on a non-empty page.
            # The next offset=500 empty page is still a valid terminator.
            # Never fabricate missing ticks or treat a short page as terminal.
            if len(data) > 500:
                out["reason"] = "HOLD_PAGINATION_PAGE_TOO_LARGE"
                return out
            raw.extend(data)
    if not out["page_terminal_verified"] or not raw:
        out["reason"] = "HOLD_PAGINATION_TERMINAL_NOT_VERIFIED"
        return out
    normal = []
    special = []
    seen = set()
    for trade in raw:
        if not isinstance(trade, dict):
            out["reason"] = "HOLD_TRADE_RECORD_INVALID"
            return out
        price, size, serial = trade.get("price"), trade.get("size"), trade.get("serial")
        if (not _real(price) or type(size) is not int or size <= 0
                or type(serial) is not int or serial < 1):
            out["reason"] = "HOLD_TRADE_PRICE_SIZE_SERIAL_INVALID"
            return out
        try:
            when = _local_micros(trade.get("time"))
        except ValueError:
            out["reason"] = "HOLD_TRADE_TIME_INVALID"
            return out
        if when.date() != source_day:
            out["reason"] = "HOLD_TRADE_DATE_MISMATCH"
            return out
        identity = (serial, trade["time"])
        if identity in seen:
            out["reason"] = "HOLD_DUPLICATED_TRADE"
            return out
        seen.add(identity)
        if serial == 99999999 and when.time() == clocktime(14, 30):
            special.append(trade)
            continue
        if not clocktime(9) <= when.time() <= clocktime(13, 30):
            out["reason"] = "HOLD_OUT_OF_REGULAR_SESSION_TRADE"
            return out
        normal.append(trade)
    if not normal:
        out["reason"] = "HOLD_NO_NORMAL_SESSION_TRADES"
        return out
    last = quote.get("lastTrade")
    total = quote.get("total")
    if not isinstance(last, dict) or not isinstance(total, dict):
        out["reason"] = "HOLD_QUOTE_LASTTRADE_OR_TOTAL_MISSING"
        return out
    try:
        observed_trade = _local_micros(last.get("time"))
    except ValueError:
        out["reason"] = "HOLD_QUOTE_TRADE_TIME_INVALID"
        return out
    matched = sum(t.get("serial") == last.get("serial")
                  and t.get("time") == last.get("time")
                  and t.get("price") == last.get("price") for t in normal)
    if (observed_trade.date() != source_day or matched != 1
            or type(total.get("transaction")) is not int
            or total["transaction"] != len(normal)):
        out["reason"] = "HOLD_LAST_TRADE_OR_TRANSACTION_IDENTITY_MISMATCH"
        return out
    out["last_trade_status"] = PASS_TRADE
    out["last_trade_tpe"] = observed_trade.isoformat()
    out["last_trade_price"] = last["price"]
    out["last_trade_serial"] = last["serial"]
    out["regular_trade_count"] = len(normal)
    out["excluded_1430_special_trade_count"] = len(special)
    out["excluded_1430_special_volume_lots"] = sum(x["size"] for x in special)
    qty = sum(t["size"] for t in normal)
    bar_qty = history.get("raw_volume_lots_sum")
    quote_qty = total.get("tradeVolume")
    if (type(quote_qty) is not int or quote_qty != qty
            or type(bar_qty) not in (int, float)
            or not math.isfinite(bar_qty) or bar_qty != qty):
        out["reason"] = "HOLD_FUGLE_SAME_SOURCE_VOLUME_MISMATCH"
        return out
    out["regular_trade_volume_lots"] = qty
    out["quote_trade_volume_lots"] = quote_qty
    out["historical_5m_volume_lots"] = bar_qty
    out["volume_status"] = PASS_VOLUME
    mean = sum(t["price"] * t["size"] for t in normal) / qty
    reported = quote.get("avgPrice")
    if not _real(reported) or abs(reported - mean) > 0.011:
        out["reason"] = "HOLD_QUOTE_AVG_PRICE_NOT_RECONCILED"
        return out
    out["weighted_mean_status"] = PASS_MEAN
    out["trades_weighted_mean_research"] = round(mean, 9)
    out["quote_avg_price"] = reported
    out["status"] = "PASS_COMPLETED_SESSION_FUGLE_SAME_SOURCE_RESEARCH_ONLY"
    out["reason"] = "FUGLE_PRIOR_SESSION_SOURCE_ARITHMETIC_CONSISTENT_NOT_EXTERNAL_PIT"
    return out
