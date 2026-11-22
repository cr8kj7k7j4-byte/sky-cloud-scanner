"""Research-only source and five-minute cadence evidence checks.

Derived from retired Shadow/PAPER_ONLY branches; intentionally contains no
paper ledger, simulated fills, trading orders, or production authorization.
The functions below do not imply actual scheduled execution.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")


def expected_five_minute_slots() -> list[str]:
    """Expected Taiwan market research slots 09:00..13:30 inclusive (55)."""
    return [
        f"{hour:02d}:{minute:02d}"
        for hour in range(9, 14)
        for minute in range(0, 60, 5)
        if hour < 13 or minute <= 30
    ]


# Formal production-daytrade research checks are five specific times, not
# the optional 55-slot five-minute research sampling cadence.
FORMAL_DAYTRADE_SLOTS = ("09:05", "09:15", "09:30", "09:50", "10:15")


def expected_formal_daytrade_slots() -> list[str]:
    """V4.0 formal Taiwan daytrade scan check times."""
    return list(FORMAL_DAYTRADE_SLOTS)


def validate_source_timestamp(value: object) -> bool:
    """Require a timezone-aware and parseable market data timestamp."""
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def evaluate_scan_artifact_readiness(
    *, eligible_successful_scans: int, artifact_files: int, records_loaded: int,
    same_run_verified: bool = False
) -> dict:
    """Fail closed when successful scans lack corresponding readable results.

    Zero eligible scans is not a strategy failure, but there is no evidence
    yet; therefore it is not considered ready for end-to-end acceptance.
    """
    scans = max(0, int(eligible_successful_scans))
    files = max(0, int(artifact_files))
    rows = max(0, int(records_loaded))
    if scans == 0:
        status = "WAITING_FOR_FIRST_ELIGIBLE_SCAN"
    elif files == 0:
        status = "SCAN_ARTIFACT_MISSING"
    elif rows == 0:
        status = "SCAN_RECORDS_MISSING"
    elif same_run_verified is not True:
        status = "SAME_RUN_ARTIFACT_UNVERIFIED"
    else:
        status = "COLLECTING"
    return {
        "status": status,
        "evidence_ready": status == "COLLECTING",
        "eligible_successful_scans": scans,
        "artifact_files": files,
        "records_loaded": rows,
        "same_run_verified": same_run_verified is True,
        "production_eligible": False,
        "live_order_enabled": False,
    }


def evaluate_cadence_observations(
    observed_slots: list[str] | None,
    *, scheduler_evidence_verified: bool = False,
    cadence_profile: str = "RESEARCH_55_SLOTS",
) -> dict:
    """Compare observed scheduled slots, never infer them from on-demand runs.

    Input must come from independently verified scheduler+artifact evidence.
    """
    if cadence_profile == "RESEARCH_55_SLOTS":
        expected = expected_five_minute_slots()
    elif cadence_profile == "FORMAL_DAYTRADE_5":
        expected = expected_formal_daytrade_slots()
    else:
        raise ValueError("UNKNOWN_CADENCE_PROFILE")
    observed = set(observed_slots or [])
    missing = [slot for slot in expected if slot not in observed]
    unexpected = sorted(observed.difference(expected))
    return {
        "cadence_profile": cadence_profile,
        "expected_slots": len(expected),
        "verified_observed_slots": len(observed.intersection(expected)),
        "missing_slots": missing,
        "unexpected_slots": unexpected,
        "cadence_evidence_complete": scheduler_evidence_verified is True and not missing and not unexpected,
        "scheduler_evidence_verified": scheduler_evidence_verified is True,
        "production_eligible": False,
    }
