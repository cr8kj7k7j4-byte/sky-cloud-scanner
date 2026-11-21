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
    *, eligible_successful_scans: int, artifact_files: int, records_loaded: int
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
    else:
        status = "COLLECTING"
    return {
        "status": status,
        "evidence_ready": status == "COLLECTING",
        "eligible_successful_scans": scans,
        "artifact_files": files,
        "records_loaded": rows,
        "production_eligible": False,
        "live_order_enabled": False,
    }


def evaluate_cadence_observations(
    observed_slots: list[str] | None,
) -> dict:
    """Compare observed scheduled slots, never infer them from on-demand runs.

    Input must come from independently verified scheduler+artifact evidence.
    """
    expected = expected_five_minute_slots()
    observed = set(observed_slots or [])
    missing = [slot for slot in expected if slot not in observed]
    unexpected = sorted(observed.difference(expected))
    return {
        "expected_slots": len(expected),
        "verified_observed_slots": len(observed.intersection(expected)),
        "missing_slots": missing,
        "unexpected_slots": unexpected,
        "cadence_evidence_complete": not missing and not unexpected,
        "production_eligible": False,
    }
