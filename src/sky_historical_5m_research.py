"""Provider-first Fugle completed-session 5m historical research contract.

Official endpoint: GET /historical/candles/{symbol} timeframe=5. 
Historical bars are NOT individual executed trades; average is NOT independent VWAP.
No automatic API request, live trade certification, positions or order execution.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, time, timedelta, timezone

TPE = timezone(timedelta(hours=8))
PASS = "PASS_COMPLETED_HISTORICAL_5M_RESEARCH_ONLY"
NO_BARS = "OBSERVATION_ONLY_NO_5M_BARS"
HOLD = "HOLD_HISTORICAL_5M_SOURCE"


def _positive(value):
    return (type(value) in (int, float) and math.isfinite(value) and value > 0)


def evaluate(symbol: str, source_date: str, payload: object, *, observed_at=None) -> dict:
    now = observed_at or datetime.now(TPE)
    result = {
        "schema": "SKY_FUGLE_HISTORICAL_5M_RESEARCH_V1",
        "symbol": symbol, "source": "Fugle Historical Candles",
        "endpoint": "/historical/candles/{symbol}", "source_date": source_date,
        "observed_at_tpe": now.astimezone(TPE).isoformat(),
        "status": HOLD, "reason": "INSUFFICIENT_HISTORICAL_SOURCE",
        "completed_bar_count": 0, "volume_raw_unit": "lots",
        "research_report_available": False, "five_minute_indicators_available": False,
        "volume_unit_cross_source_certified": False,
        "independent_vwap_certified": False, "executed_trade_time_certified": False,
        "production_eligible": False, "execution_authorized": False,
        "automatic_order": False, "trade_action": "禁止交易",
    }
    if not (isinstance(symbol, str) and re.fullmatch(r"[0-9]{4,6}", symbol)
            and isinstance(source_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", source_date)):
        result["reason"] = "INVALID_SYMBOL_OR_SOURCE_DATE"
        return result
    try:
        target = date.fromisoformat(source_date)
        local_now = now.astimezone(TPE)
    except (TypeError, ValueError, OverflowError):
        result["reason"] = "INVALID_DATE"
        return result
    if target >= local_now.date() or target.weekday() >= 5:
        result["reason"] = "NOT_PREVIOUS_COMPLETED_WEEKDAY"
        return result
    if not isinstance(payload, dict):
        return result
    if (payload.get("symbol") != symbol or payload.get("timeframe") != "5"
            or payload.get("exchange") not in ("TWSE", "TPEx")):
        result["reason"] = "HISTORICAL_IDENTITY_MISMATCH"
        return result
    raw = payload.get("data")
    if not isinstance(raw, list):
        result["reason"] = "HISTORICAL_ROWS_MISSING_OR_INVALID"
        return result
    # No minimum number of bars is required to issue a dated research report.
    # [] is a valid no-observation case; it does NOT certify any indicators,
    # executed trades, full-session volume, VWAP, or an actionable signal.
    if not raw:
        result.update({
            "status": NO_BARS,
            "reason": "NO_OBSERVED_5M_BARS_RESEARCH_CONTINUES",
            "research_report_available": True,
            "five_minute_indicators_available": False,
            "observed_regular_slot_count": 0,
            "missing_regular_slot_count": 53,
            "closing_auction_bar_observed": False,
            "session_coverage_certified": False,
            "cross_source_reconciliation_certified": False,
            "bars": [],
            "raw_volume_lots_sum": None,
            "last_completed_bar_start_tpe": None,
            "closing_auction_bar_start_tpe": None,
            "average_semantics": "NO_DATA_NO_VWAP",
        })
        return result
    # Data validation still rejects corrupt/duplicated/out-of-session bars.
    # No fixed count is a prerequisite for research; slots are used only to
    # check timestamp semantics and disclose observed coverage.

    times = []
    volume_total = 0.0
    observations = []
    for row in raw:
        if not isinstance(row, dict) or not isinstance(row.get("date"), str):
            result["reason"] = "INVALID_BAR"
            return result
        try:
            dt = datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
        except ValueError:
            result["reason"] = "INVALID_BAR_TIME"
            return result
        if (dt.tzinfo is None or dt.utcoffset() != timedelta(hours=8)
                or dt.date() != target or dt.second != 0 or dt.microsecond != 0
                or dt.minute % 5 != 0 or not time(9, 0) <= dt.time() <= time(13, 30)):
            result["reason"] = "BAR_TIME_OR_SESSION_INVALID"
            return result
        op, hi, lo, close, vol, avg = (row.get(k) for k in
                                      ("open", "high", "low", "close", "volume", "average"))
        if (not all(_positive(p) for p in (op, hi, lo, close, avg))
                or type(vol) not in (int, float) or not math.isfinite(vol) or vol <= 0
                or not lo <= min(op, close) <= max(op, close) <= hi):
            result["reason"] = "INVALID_OHLC_VOLUME_OR_AVERAGE"
            return result
        times.append(dt)
        volume_total += vol
        observations.append({"start_tpe": dt.isoformat(), "open": op, "high": hi,
                             "low": lo, "close": close, "volume_lots": vol,
                             "provider_cumulative_average": avg})
    if (len(set(times)) != len(times)
            or not all(a < b for a, b in zip(times, times[1:]))):
        result["reason"] = "DUPLICATE_OR_UNSORTED_BAR"
        return result
    # Provider-first: Fugle explicitly omits minutes without trades. The
    # regular session has 09:00–13:20 5m starts (53 possible slots); 13:25
    # is the closing call-auction interval and NEVER a normal bar.
    # A separate 13:30 bar may appear only when the closing auction traded.
    # Missing slots are an observable coverage gap, NOT invalid source data.
    regular_slots = [datetime.combine(target, time(9), TPE)
                     + timedelta(minutes=5 * i) for i in range(53)]
    auction = datetime.combine(target, time(13, 30), TPE)
    regular_slot_set = set(regular_slots)
    allowed = regular_slot_set | {auction}
    if any(t not in allowed for t in times):
        result["reason"] = "BAR_OUTSIDE_OFFICIAL_5M_SLOTS"
        return result
    regular_observed = sum(t in regular_slot_set for t in times)
    missing_regular = len(regular_slots) - regular_observed
    auction_present = auction in times
    # The 13:30 closing bar is separate and not proof of continuous trades.
    # No daily coverage or cross-source claim is inferred from sparse bars.
    result.update({
        "status": PASS, "reason": "HISTORICAL_SPARSE_BARS_VALIDATED_RESEARCH_ONLY",
        "research_report_available": True, "five_minute_indicators_available": True,
        "completed_bar_count": len(times), "raw_volume_lots_sum": volume_total,
        "last_completed_bar_start_tpe": times[-1].isoformat(),
        "closing_auction_bar_start_tpe": auction.isoformat() if auction_present else None,
        "observed_regular_slot_count": regular_observed,
        "missing_regular_slot_count": missing_regular,
        "closing_auction_bar_observed": auction_present,
        "session_coverage_certified": False,
        "cross_source_reconciliation_certified": False,
        "bars": observations,
        # Strictly research-only: cumulative average is provider-reported
        # and must never become independent VWAP or an executed trade.
        "average_semantics": "PROVIDER_CUMULATIVE_SINCE_OPEN_NOT_INDEPENDENT_VWAP",
    })
    return result
