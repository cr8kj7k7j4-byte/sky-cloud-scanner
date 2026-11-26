"""Pure, read-only session policy for Sky daytrade research.

This is a selector, not an exchange calendar, quote fetcher, scanner, or
permission to trade. A trading-day decision must come from verified official
calendar/source evidence; never infer that Monday-Friday guarantees a session.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

TPE = timezone(timedelta(hours=8))
OPEN = time(9, 0)
CLOSE = time(13, 30)


def daytrade_session_policy(
    observed_at: datetime,
    *,
    trading_day_verified: bool | None = None,
    latest_complete_session_date: str | None = None,
) -> dict:
    """Select evidence needs without fabricating a session or historical data.

    trading_day_verified=True must be backed by separately verified exchange
    calendar/session evidence from the caller; None means unavailable.
    latest_complete_session_date is a label, not proof of a usable artifact.
    """
    if not isinstance(observed_at, datetime) or observed_at.tzinfo is None:
        raise ValueError("timezone_aware_datetime_required")
    if trading_day_verified not in (True, False, None):
        raise ValueError("invalid_trading_day_verification")

    now = observed_at.astimezone(TPE)
    local_clock = now.time().replace(tzinfo=None)
    if trading_day_verified is False:
        mode = "NON_TRADING_DAY_RESEARCH"
    elif local_clock < OPEN:
        mode = "PREMARKET_RESEARCH"
    elif local_clock <= CLOSE:
        mode = ("INTRADAY_A1_A2" if trading_day_verified is True
                else "INTRADAY_CALENDAR_UNVERIFIED_RESEARCH")
    else:
        mode = "POSTMARKET_RESEARCH"

    live = mode == "INTRADAY_A1_A2"
    return {
        "schema": "SKY_DAYTRADE_SESSION_POLICY_V1",
        "observed_at_tpe": now.isoformat(),
        "session_mode": mode,
        "trading_day_verified": trading_day_verified,
        "latest_complete_session_date": latest_complete_session_date,
        "historical_artifact_verified": False,
        "allow_research_readback": True,
        "requires_a1_a2_for_new_entry": True,
        "allow_live_quote_claim": live,
        "new_entry_authorized": False,
        "action": "等待",
        "status": "HOLD_EVIDENCE",
        "notes": (
            "Session routing is not a scan. Historical research needs dated, "
            "authorized, complete source artifact; a live entry separately "
            "needs current-session Fugle A1/A2, strategy, costs and P0-R."
        ),
    }
