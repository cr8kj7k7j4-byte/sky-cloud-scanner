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


def read_swing_complete_session_observations(
    observed_at: datetime,
    extraction_root,
    *,
    trading_day_verified: bool | None,
    expected_run_id: str,
    expected_attempt: str,
    expected_head_sha: str,
    artifact_id: int,
    verified_complete_session_date: str,
    calendar_session_certified: bool,
) -> dict:
    """Consume verified historical bytes for swing *observation*, never a V1.0 signal.

    The caller supplies an independently downloaded same-run Artifact and
    certified official exchange session. No network, calendar inference,
    live scan, trade authorization, or paid API call occurs here.
    """
    policy = swing_session_policy(
        observed_at,
        trading_day_verified=trading_day_verified,
        latest_complete_session_date=verified_complete_session_date,
    )
    if not policy["allow_historical_readback"]:
        raise ValueError("LIVE_SESSION_REQUIRES_AUTHORIZED_A1_A2")
    if not verified_complete_session_date or not calendar_session_certified:
        raise ValueError("SWING_OFFICIAL_COMPLETE_SESSION_REQUIRED")
    from .sky_historical_research_readback import read_complete_session_research

    history = read_complete_session_research(
        extraction_root,
        expected_run_id=expected_run_id,
        expected_attempt=expected_attempt,
        expected_head_sha=expected_head_sha,
        artifact_id=artifact_id,
        verified_complete_session_date=verified_complete_session_date,
        calendar_session_certified=calendar_session_certified,
    )
    return {
        "schema": "SKY_SWING_COMPLETE_SESSION_OBSERVATIONS_V1",
        "status": "HISTORICAL_OBSERVATION_ONLY_NO_SWING_SIGNAL",
        "session_mode": policy["session_mode"],
        "production_strategy": "Sky Swing V1.0",
        "exact_v1_rule_status": "BLOCKED_EXACT_RULE_SPEC",
        "source_certified": False,
        "strategy_signal_verified": False,
        "historical_artifact_verified": True,
        "historical_evidence": history,
        "run_id": history["run_id"],
        "head_sha": history["head_sha"],
        "artifact_id": history["artifact_id"],
        "source_session_date": history["source_session_date"],
        "new_entry_authorized": False,
        "production_eligible": False,
        "automatic_orders": False,
        "trade_action": "禁止交易",
        "notes": "Generic cross-market history, not independently validated Swing V1.0 signal.",
    }
