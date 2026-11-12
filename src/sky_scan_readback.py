"""Read-only Sky command alias + GitHub scan receipt freshness contract.

Integrate into the existing Chat Bridge only after PR #510 reconciliation.
Snapshot capture time never substitutes for executed-trade timestamp.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

CANONICAL_COMMAND = "Sky 快掃"
COMMANDS = frozenset({
    "Sky 快掃", "Sky 快掃更新", "Sky 當沖現在掃一次",
    "Sky 當沖快掃", "Sky v1.4 Dynamic Capital Rotation 掃一下",
})
STATUS_SCHEMA = "SKY_CHAT_SCAN_STATUS_V1"


def canonical_command(command: str) -> str:
    if command not in COMMANDS:
        raise ValueError("UNSUPPORTED_SKY_COMMAND")
    return CANONICAL_COMMAND


def _parse_time(value: Any, key: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{key}_MISSING")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key}_INVALID") from exc
    if stamp.utcoffset() is None:
        raise ValueError(f"{key}_TIMEZONE_REQUIRED")
    return stamp.astimezone(timezone.utc)


def validate_scan_readback(
    status: dict[str, Any], *,
    expected_run_id: str,
    expected_request_id: str,
    now: datetime | None = None,
    max_receipt_age_seconds: int = 300,
    max_capture_age_seconds: int = 300,
) -> dict[str, Any]:
    """Fail closed on stale/foreign status; return research-only readback.

    A fresh receipt is NOT a fresh executed trade or a production trading signal.
    """
    if not isinstance(status, dict) or status.get("schema") != STATUS_SCHEMA:
        raise ValueError("INVALID_STATUS_SCHEMA")
    if not expected_run_id or str(status.get("scan_id")) != str(expected_run_id):
        raise ValueError("RUN_ID_MISMATCH")
    if not expected_request_id or status.get("request_id") != expected_request_id:
        raise ValueError("REQUEST_ID_MISMATCH")
    url = status.get("run_url")
    if not isinstance(url, str) or not url.startswith(
        "https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/"
    ) or url.rsplit("/", 1)[-1] != str(expected_run_id):
        raise ValueError("RUN_URL_MISMATCH")
    if status.get("production_eligible") is not False or status.get("automatic_order") is not False:
        raise ValueError("RESEARCH_ONLY_GUARD_FAILED")
    if not isinstance(max_receipt_age_seconds, int) or max_receipt_age_seconds < 0:
        raise ValueError("INVALID_MAX_AGE")
    current = now or datetime.now(timezone.utc)
    if current.utcoffset() is None:
        raise ValueError("NOW_TIMEZONE_REQUIRED")
    current = current.astimezone(timezone.utc)
    completed = _parse_time(status.get("completed_at_utc"), "COMPLETED_AT")
    age = (current - completed).total_seconds()
    if age < -30:
        raise ValueError("RECEIPT_FROM_FUTURE")
    if age > max_receipt_age_seconds:
        raise ValueError("STALE_RECEIPT")
    if status.get("status") != "REPORT_READY_RESEARCH_ONLY":
        raise ValueError("SCAN_NOT_REPORT_READY")
    if status.get("source") != "FUGLE_PAID_SNAPSHOT":
        raise ValueError("UNVERIFIED_SOURCE")
    count = status.get("row_count")
    universe = status.get("universe_count")
    if (type(count) is not int or type(universe) is not int
            or count <= 0 or universe <= 0 or count != universe):
        raise ValueError("REPORT_COUNT_MISMATCH")
    observed = status.get("observed_price_count")
    verified = status.get("stage2_verified_executed_count")
    if (type(observed) is not int or not 0 <= observed <= universe
            or type(verified) is not int or verified < 0):
        raise ValueError("INVALID_COVERAGE_COUNTS")
    captured = _parse_time(status.get("data_timestamp"), "SNAPSHOT_CAPTURE_AT")
    if captured > current + timedelta(seconds=30):
        raise ValueError("SNAPSHOT_CAPTURE_IN_FUTURE")
    if not isinstance(max_capture_age_seconds, int) or max_capture_age_seconds < 0:
        raise ValueError("INVALID_CAPTURE_MAX_AGE")
    if (current - captured).total_seconds() > max_capture_age_seconds:
        raise ValueError("STALE_SNAPSHOT_CAPTURE")
    # Capture time is a provenance field, NEVER verified trade execution time.
    return {
        "status": "RESEARCH_REPORT_READABLE_NOT_TRADE_CERTIFIED",
        "run_id": expected_run_id,
        "request_id": expected_request_id,
        "receipt_age_seconds": round(max(0.0, age), 1),
        "snapshot_capture_at": captured.isoformat(),
        "snapshot_is_executed_trade_time": False,
        "observed_price_count": observed,
        "stage2_verified_executed_count": verified,
        "production_eligible": False,
        "automatic_order": False,
        "trade_action": "禁止交易",
    }
