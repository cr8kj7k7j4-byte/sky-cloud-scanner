"""Read-only Sky swing research session selector; never fetches quotes or trades."""
from __future__ import annotations

from datetime import datetime

from .sky_daytrade_session_policy import daytrade_session_policy


def swing_session_policy(
    observed_at: datetime,
    *,
    trading_day_verified: bool | None = None,
    latest_complete_session_date: str | None = None,
) -> dict:
    """Classify evidence needs; no historical Artifact is trusted by default.

    An external caller MUST independently verify exchange calendar and historical
    Artifact identity, date, completeness, source and digest before presenting
    research values. The legacy live scanner must not be run for stale history.
    """
    base = daytrade_session_policy(
        observed_at,
        trading_day_verified=trading_day_verified,
        latest_complete_session_date=latest_complete_session_date,
    )
    mode = base["session_mode"]
    live = mode == "INTRADAY_A1_A2"
    return {
        "schema": "SKY_SWING_SESSION_POLICY_V1",
        "observed_at_tpe": base["observed_at_tpe"],
        "session_mode": mode,
        "trading_day_verified": trading_day_verified,
        "latest_complete_session_date": latest_complete_session_date,
        "research_source_mode": (
            "AUTHORIZED_LIVE_OBSERVATION_REQUIRED" if live
            else "VERIFIED_COMPLETE_SESSION_ARTIFACT_REQUIRED"
        ),
        "command_accepted": True,
        "command_availability": "ALL_SESSIONS",
        "report_available": False,
        "report_unavailable_reason": "HISTORICAL_OR_LIVE_SOURCE_EVIDENCE_NOT_ATTACHED",
        "historical_artifact_verified": False,
        "allow_historical_readback": not live,
        "allow_live_scan": live,
        "production_strategy": "Sky Swing V1.0",
        "exact_v1_rule_status": "BLOCKED_EXACT_RULE_SPEC",
        "new_entry_authorized": False,
        "status": "HOLD_EVIDENCE",
        "action": "等待",
        "notes": (
            "Selector only. No GitHub dispatch, live price certification, "
            "artifact retrieval, governed Swing V1.0 signal or order."
        ),
    }
