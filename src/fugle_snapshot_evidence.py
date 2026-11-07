"""Screening-only validation of Fugle bulk snapshot rows.

A snapshot lastUpdated timestamp is not the individual last executed-trade
timestamp. Passing this validator NEVER certifies an executable quote.
"""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
from .realtime_quote_evidence import timestamp_tpe

TPE = ZoneInfo("Asia/Taipei")


def validate_snapshot_screening_rows(universe, rows, now=None, *,
                                     min_coverage_pct=80.0, min_exchange_pct=70.0,
                                     max_age_seconds=180):
    now = now or datetime.now(TPE)
    by_symbol = {str(x.get("symbol")): x for x in universe}
    target = {key: sum(x.get("exchange") == key for x in universe)
              for key in ("TWSE", "TPEx")}
    accepted = {}
    rejected = {}
    for row in rows:
        symbol = str(row.get("symbol") or "")
        meta = by_symbol.get(symbol)
        status = None
        if meta is None or meta.get("exchange") not in target:
            status = "NOT_IN_UNIVERSE"
        elif row.get("quote_source") != "Fugle bulk snapshot":
            status = "NOT_FUGLE_SNAPSHOT"
        elif str(row.get("quote_date")) != now.date().isoformat():
            status = "WRONG_SESSION_DATE"
        else:
            ts = timestamp_tpe(row.get("quote_time"))
            try:
                price = float(row.get("last"))
                volume = float(row.get("volume"))
            except (TypeError, ValueError, OverflowError):
                price, volume = 0.0, 0.0
            age = (now - ts).total_seconds() if ts else None
            if ts is None or ts.date() != now.date() or age is None or not -30 <= age <= max_age_seconds:
                status = "STALE_OR_MISSING_SNAPSHOT_TIME"
            elif price <= 0 or volume <= 0:
                status = "NO_TRADE_PRICE_OR_VOLUME"
        if status:
            rejected[status] = rejected.get(status, 0) + 1
        else:
            accepted[symbol] = row
    counts = {key: sum(by_symbol[s]["exchange"] == key for s in accepted)
              for key in target}
    rates = {key: round(100 * counts[key] / target[key], 2) if target[key] else 0
             for key in target}
    coverage = round(100 * len(accepted) / len(by_symbol), 2) if by_symbol else 0
    passed = bool(by_symbol and coverage >= min_coverage_pct
                  and all(target[key] and rates[key] >= min_exchange_pct for key in target))
    return {
        "status": "PASS_SNAPSHOT_SCREENING_ONLY" if passed else "BLOCKED_SNAPSHOT_SCREENING",
        "snapshot_screening_ok": passed,
        "valid_quote_count": len(accepted),
        "quote_coverage_pct": coverage,
        "by_exchange": {key: {"universe": target[key], "valid": counts[key],
                               "coverage_pct": rates[key]} for key in target},
        "rejected": rejected,
        "quote_scope": "WHOLE_MARKET_SNAPSHOT_SCREENING_ONLY" if passed else "PARTIAL_SNAPSHOT_SCREENING",
        "live_whole_market_certified": False,
        "last_execution_verified": False,
        "data_time": now.isoformat(),
        "accepted_rows": list(accepted.values()),
    }
