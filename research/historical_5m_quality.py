"""Fugle five-minute historical candle integrity: observational, not fill evidence.

Detects structural/data errors and reports per-session coverage. Does not assume
each weekday was a trading day or each illiquid symbol traded every five minutes.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, time
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")
SESSION_START = time(9, 0)
SESSION_END = time(13, 30)


def inspect_history(rows, start="2026-01-01", end="2026-11-07"):
    if not isinstance(rows, list):
        return {"status": "INVALID_DATA", "reason": "NOT_LIST", "session_counts": {}}
    counts = Counter()
    invalid = Counter()
    parsed = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            invalid["non_object"] += 1
            continue
        try:
            stamp = datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                invalid["missing_timezone"] += 1
                continue
            local = stamp.astimezone(TAIPEI)
        except (KeyError, TypeError, ValueError, AttributeError):
            invalid["invalid_timestamp"] += 1
            continue
        key = local.isoformat()
        if key in seen:
            invalid["duplicate_timestamp"] += 1
        seen.add(key)
        parsed.append(local)
        d = local.date().isoformat()
        if not (start <= d <= end):
            invalid["outside_requested_range"] += 1
        if local.weekday() >= 5:
            invalid["weekend_candle"] += 1
        if not (SESSION_START <= local.time().replace(tzinfo=None) <= SESSION_END):
            invalid["outside_regular_session"] += 1
        if local.minute % 5 or local.second or local.microsecond:
            invalid["unaligned_5min_timestamp"] += 1
        try:
            o,h,l,c,v = (float(row[k]) for k in ("open","high","low","close","volume"))
            if not (0 < l <= min(o,c) <= max(o,c) <= h and v >= 0):
                invalid["invalid_ohlcv_relationship"] += 1
        except (KeyError, TypeError, ValueError, OverflowError):
            invalid["invalid_ohlcv_values"] += 1
        counts[d] += 1
    chronology_invalid = any(a > b for a,b in zip(parsed,parsed[1:]))
    if chronology_invalid:
        invalid["non_ascending_timestamps"] += 1
    # 09:00 through 13:30 inclusive gives 55 potential clock positions.
    # This is an upper bound, not an obligation for illiquid stocks to trade.
    overfull = sorted(day for day,num in counts.items() if num > 55)
    if overfull:
        invalid["more_than_55_slots_per_session"] += len(overfull)
    return {
        "status": "INVALID_DATA" if invalid else ("DATA_OBSERVED" if rows else "EMPTY"),
        "row_count": len(rows),
        "distinct_session_dates": len(counts),
        "session_counts": dict(sorted(counts.items())),
        "daily_min_bars": min(counts.values()) if counts else None,
        "daily_max_bars": max(counts.values()) if counts else None,
        "weekday_sessions_below_55_bars": sum(1 for n in counts.values() if n < 55),
        "invalid_counts": dict(sorted(invalid.items())),
        "potential_session_slots_not_verified": True,
        "official_holiday_calendar_reconciled": False,
        "missing_trading_days_verified": False,
        "full_period_complete": False,
        "reason": "Sparse bars can reflect no trades; holidays and suspensions require official reconciliation."
    }
