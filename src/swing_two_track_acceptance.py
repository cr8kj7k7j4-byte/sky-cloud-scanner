"""Two independent RESEARCH acceptance lanes for existing Swing scanner artifacts.

This module never approves a trade, a full-market executed feed or Production.
"""
from __future__ import annotations

from datetime import date as calendar_date, datetime
import math
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")


def _time(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.astimezone(TPE) if stamp.utcoffset() is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _day(value):
    stamp = _time(value)
    return stamp.date().isoformat() if stamp is not None else None


def _current_trade(confirmation, scan_started):
    price = confirmation.get("verified_executed_price")
    traded = _time(confirmation.get("verified_executed_at"))
    checked_at = _time(confirmation.get("individual_checked_at_tpe"))
    return (
        confirmation.get("data_status") == "FRESH_EXECUTED_TRADE"
        and isinstance(price, (float, int)) and not isinstance(price, bool)
        and math.isfinite(price) and price > 0
        and traded is not None and checked_at is not None and scan_started is not None
        and checked_at.date() == scan_started.date() == traded.date()
        and 0 <= (checked_at - scan_started).total_seconds() <= 600
        and 0 <= (checked_at - traded).total_seconds() <= 180
    )


def _snapshot_detail_consistent(report, snapshot, received):
    """Check complete observation evidence without treating snapshots as executed trades."""
    observed = snapshot.get("data")
    stamp = _time(snapshot.get("generated_at"))
    if (not isinstance(observed, list) or not observed or received is None
            or stamp is None or stamp.date() != received.date()
            or not 0 <= (received - stamp).total_seconds() <= 180):
        return False
    n = len(observed)
    if (not isinstance(snapshot.get("observed_symbols"), int)
            or isinstance(snapshot["observed_symbols"], bool)
            or snapshot["observed_symbols"] != n
            or not isinstance(report.get("unverified_snapshot_observation_count"), int)
            or isinstance(report["unverified_snapshot_observation_count"], bool)
            or report["unverified_snapshot_observation_count"] != n):
        return False
    symbols = set()
    by_exchange = {"TWSE": 0, "TPEx": 0}
    for row in observed:
        if not isinstance(row, dict):
            return False
        symbol = row.get("symbol")
        exchange = row.get("exchange")
        if (not isinstance(symbol, str) or not symbol.strip()
                or symbol in symbols or exchange not in by_exchange):
            return False
        symbols.add(symbol)
        by_exchange[exchange] += 1
    counts = report.get("snapshot_exchange_counts") or {}
    return all(
        isinstance(counts.get(ex), int) and not isinstance(counts[ex], bool)
        and by_exchange[ex] <= counts[ex]
        for ex in by_exchange
    )


def assess(report, snapshot):
    """Classify evidence, never promote individually verified trades to market coverage."""
    result = {
        "schema": "SKY_SWING_TWO_TRACK_ACCEPTANCE_V1",
        "snapshot_screen_status": "HOLD_SNAPSHOT_EVIDENCE",
        "dated_snapshot_research_status": "HOLD_DATED_SNAPSHOT_RESEARCH_EVIDENCE",
        "dated_snapshot_source_date": None,
        "candidate_execution_status": "HOLD_CANDIDATE_EXECUTION_EVIDENCE",
        "candidate_trade_gate": "HOLD_FULL_STRATEGY_AND_RISK_NOT_VERIFIED",
        "full_market_execution_certification_status": "HOLD_FULL_MARKET_EXECUTED_TRADE_TIME",
        "production_eligible": False,
        "automatic_order": False,
        "trade_action": "禁止交易",
    }
    if not isinstance(report, dict) or not isinstance(snapshot, dict):
        return result
    received = _time(report.get("generated_at"))
    report_day = _day(report.get("generated_at"))
    health = (report.get("source_health") or {}).get("official_universe") or {}
    counts = report.get("snapshot_exchange_counts") or {}
    size = report.get("universe_count")
    pct = report.get("snapshot_coverage_pct")
    if (report_day and _snapshot_detail_consistent(report, snapshot, received)
            and snapshot.get("source") == "Fugle bulk snapshot"
            and _day(snapshot.get("generated_at")) == report_day
            and snapshot.get("observed_symbols", 0) > 0
            and isinstance(snapshot.get("data"), list)
            and all(isinstance(x, dict)
                    and x.get("source") == "Fugle bulk snapshot"
                    and x.get("snapshot_date") == report_day
                    and x.get("strategy_signal") is False
                    and x.get("production_eligible") is False
                    for x in snapshot["data"])
            and isinstance(size, int) and not isinstance(size, bool) and size > 0
            and isinstance(pct, (int, float)) and not isinstance(pct, bool)
            and 80 <= pct <= 100
            and all(type(health.get(m)) is int and health[m] > 0
                    and isinstance(counts.get(ex), int)
                    and 0 <= counts[ex] <= health[m]
                    and 100 * counts[ex] / health[m] >= 70
                    for ex, m in (("TWSE", "twse"), ("TPEx", "tpex")))
            and all(report.get(f) is False for f in
                    ("observations_are_trade_signals",))):
        result["snapshot_screen_status"] = "PASS_SNAPSHOT_OBSERVATION_ONLY"
    # A separate, strictly dated historical observation lane. It must NOT
    # make same-day snapshot, individual execution, market or strategy gates pass.
    # Only a single provider source date within seven days and with independent
    # complete source-row verification is eligible for research-only display.
    dated_source = report.get("dated_research_source_date")
    try:
        source_day = calendar_date.fromisoformat(dated_source)
        scan_day = received.date() if received is not None else None
        age = (scan_day - source_day).days if scan_day is not None else -1
    except (TypeError, ValueError, OverflowError):
        source_day, age = None, -1
    snapshot_rows = snapshot.get("data")
    market_sizes = report.get("source_health", {}).get("official_universe", {})
    dated_ok = (
        source_day is not None and 1 <= age <= 7 and source_day.weekday() < 5
        and _snapshot_detail_consistent(report, snapshot, received)
        and snapshot.get("source") == "Fugle bulk snapshot"
        and isinstance(snapshot_rows, list) and bool(snapshot_rows)
        and report.get("observations_are_trade_signals") is False
        and report.get("operational_full_market_scan") is False
        and report.get("market_data_gate") == "BLOCKED_EXTERNAL_DATA_NO_TRADE"
        and report.get("dated_research_is_live") is False
        and report.get("candidate_count") == 0
        and report.get("quote_count") == 0
        and isinstance(size, int) and not isinstance(size, bool) and size > 0
        and isinstance(pct, (int, float)) and not isinstance(pct, bool)
        and math.isfinite(pct) and 80 <= pct <= 100
        and all(type(market_sizes.get(m)) is int and market_sizes[m] > 0
                and type(counts.get(ex)) is int
                and 100 * counts[ex] / market_sizes[m] >= 70
                and counts[ex] <= market_sizes[m]
                for ex, m in (("TWSE", "twse"), ("TPEx", "tpex")))
        and all(
            isinstance(x, dict)
            and x.get("source") == "Fugle bulk snapshot"
            and x.get("snapshot_date") == dated_source
            and x.get("strategy_signal") is False
            and x.get("production_eligible") is False
            and x.get("data_status") == "UNVERIFIED_EXECUTED_TRADE_TIME"
            and isinstance(x.get("indicative_last_price"), (int, float))
            and not isinstance(x.get("indicative_last_price"), bool)
            and math.isfinite(x["indicative_last_price"])
            and x["indicative_last_price"] > 0
            for x in snapshot_rows
        )
    )
    if dated_ok:
        result["dated_snapshot_research_status"] = "PASS_DATED_SNAPSHOT_RESEARCH_ONLY"
        result["dated_snapshot_source_date"] = dated_source
    confirmations = report.get("snapshot_individual_confirmation")
    if (isinstance(confirmations, list)
            and confirmations
            and all(isinstance(x, dict)
                    and x.get("strategy_signal") is False
                    and x.get("production_eligible") is False
                    for x in confirmations)
            and any(_current_trade(x, received)
            for x in confirmations)):
        result["candidate_execution_status"] = "PASS_BOUNDED_INDIVIDUAL_EXECUTION_ONLY"
    # Keep the original canonical market gate entirely independent of observations.
    if (report.get("operational_full_market_scan") is True
            and report.get("live_whole_market_certified") is True
            and report.get("quote_scope") == "WHOLE_MARKET_EXECUTED_LIVE"
            and report.get("market_data_gate") ==
                "PASS_OPERATIONAL_WHOLE_MARKET_LIVE_RESEARCH_ONLY"
            and (report.get("live_market_evidence") or {}).get(
                "valid_whole_market_operational") is True):
        result["full_market_execution_certification_status"] = (
            "PASS_ORIGINAL_FULL_MARKET_EXECUTION_GATE"
        )
    return result
