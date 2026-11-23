"""Two independent RESEARCH acceptance lanes for existing Swing scanner artifacts.

This module never approves a trade, a full-market executed feed or Production.
"""
from __future__ import annotations

from datetime import datetime
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


def _current_trade(confirmation, received):
    price = confirmation.get("verified_executed_price")
    traded = _time(confirmation.get("verified_executed_at"))
    return (
        confirmation.get("data_status") == "FRESH_EXECUTED_TRADE"
        and isinstance(price, (float, int)) and not isinstance(price, bool)
        and math.isfinite(price) and price > 0
        and traded is not None and received is not None
        and traded.date() == received.date()
        and 0 <= (received - traded).total_seconds() <= 180
    )


def assess(report, snapshot):
    """Classify evidence, never promote individually verified trades to market coverage."""
    result = {
        "schema": "SKY_SWING_TWO_TRACK_ACCEPTANCE_V1",
        "snapshot_screen_status": "HOLD_SNAPSHOT_EVIDENCE",
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
    if (report_day and snapshot.get("source") == "Fugle bulk snapshot"
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
            and all(isinstance(health.get(m), int) and health[m] > 0
                    and isinstance(counts.get(ex), int)
                    and 0 <= counts[ex] <= health[m]
                    and 100 * counts[ex] / health[m] >= 70
                    for ex, m in (("TWSE", "twse"), ("TPEx", "tpex")))
            and all(report.get(f) is False for f in
                    ("observations_are_trade_signals",))):
        result["snapshot_screen_status"] = "PASS_SNAPSHOT_OBSERVATION_ONLY"
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
