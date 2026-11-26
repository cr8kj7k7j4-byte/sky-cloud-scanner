"""Research-only historical artifact readback for Sky off-hours quick scans.

Caller supplies independently downloaded GitHub Artifact bytes and metadata.
No network, Fugle API, market calendar inference, trade signals or orders.
"""
from __future__ import annotations

import json
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

from .sky_same_run_artifact_verify import verify_downloaded_inventory
from research.sky_13col_report import render, projection

TPE = timezone(timedelta(hours=8))
SOURCE_KEY = "full_market_reference"
SOURCE_PATH = "output/sky_quickscan_information/full_universe.json"


def read_complete_session_research(
    extraction_root: str | Path,
    *,
    expected_run_id: str,
    expected_attempt: str,
    expected_head_sha: str,
    artifact_id: int,
    verified_complete_session_date: str,
    calendar_session_certified: bool,
) -> dict:
    """Validate an already-downloaded same-run historical source.

    Independent downloader must verify artifact_id belongs to expected Run.
    calendar_session_certified must be authenticated externally (TWSE/TPEx).
    A valid SHA proves bytes, not Fugle entitlement or executed-trade time.
    """
    if calendar_session_certified is not True:
        raise ValueError("OFFICIAL_SESSION_NOT_CERTIFIED")
    if not isinstance(verified_complete_session_date, str):
        raise ValueError("SESSION_DATE_REQUIRED")
    try:
        session_date = date.fromisoformat(verified_complete_session_date)
    except ValueError as exc:
        raise ValueError("INVALID_VERIFIED_SESSION_DATE") from exc
    integrity = verify_downloaded_inventory(
        extraction_root,
        expected_run_id=expected_run_id,
        expected_attempt=expected_attempt,
        expected_head_sha=expected_head_sha,
        artifact_id=artifact_id,
    )
    root = Path(extraction_root).resolve(strict=True)
    manifest_path = root / "output/sky_quickscan_information/same_run_source_inventory.json"
    inventory = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = inventory["source_inventory"].get(SOURCE_KEY)
    if (not isinstance(source, dict)
            or source.get("path") != SOURCE_PATH
            or source.get("status") != "FILE_PRESENT_NOT_SOURCE_CERTIFIED"
            or not isinstance(source.get("sha256"), str)):
        raise ValueError("FULL_MARKET_REFERENCE_NOT_VERIFIED")
    source_file = root / SOURCE_PATH
    if not source_file.is_file() or source_file.is_symlink():
        raise ValueError("FULL_MARKET_REFERENCE_MISSING")
    report = json.loads(source_file.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("schema") != "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1":
        raise ValueError("INVALID_HISTORICAL_REPORT_SCHEMA")
    checked = report.get("checked_at_tpe")
    if not isinstance(checked, str):
        raise ValueError("HISTORICAL_DATA_TIME_MISSING")
    try:
        stamp = datetime.fromisoformat(checked)
    except ValueError as exc:
        raise ValueError("INVALID_HISTORICAL_DATA_TIME") from exc
    # Capture time can be later than the officially certified source session.
    # Never relabel a prior-session Snapshot as an execution on capture day.
    if stamp.tzinfo is None or stamp.astimezone(TPE).date() < session_date:
        raise ValueError("HISTORICAL_CAPTURE_BEFORE_SESSION")
    rows = report.get("all_symbols")
    count = report.get("universe_count")
    if (not isinstance(rows, list) or not rows or type(count) is not int
            or count != len(rows)):
        raise ValueError("HISTORICAL_UNIVERSE_INCOMPLETE")
    symbols = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("INVALID_HISTORICAL_ROW")
        symbol = item.get("symbol")
        if not isinstance(symbol, str) or not symbol or symbol in symbols:
            raise ValueError("INVALID_OR_DUPLICATE_HISTORICAL_SYMBOL")
        symbols.add(symbol)
        source_date = item.get("snapshot_source_date")
        if source_date != verified_complete_session_date:
            raise ValueError("HISTORICAL_SOURCE_SESSION_MISMATCH")
        observed = item.get("snapshot_observed_at")
        if observed is not None:
            try:
                observed_time = datetime.fromisoformat(observed)
            except (TypeError, ValueError) as exc:
                raise ValueError("INVALID_HISTORICAL_ROW_TIME") from exc
            # Observed-at is a capture timestamp, not the source trade date.
            # It must not precede the certified session or exceed report capture.
            if (observed_time.tzinfo is None
                    or observed_time.astimezone(TPE).date() < session_date
                    or observed_time.astimezone(TPE) > stamp.astimezone(TPE)):
                raise ValueError("HISTORICAL_ROW_CAPTURE_TIME_INVALID")
    markdown = render(report)
    return {
        "schema": "SKY_COMPLETE_SESSION_HISTORICAL_READBACK_V1",
        "status": "HISTORICAL_BYTES_READABLE_RESEARCH_ONLY",
        "source_certified": False,
        "source_certification_reason": (
            "同次 SHA-256 僅證明下載位元組完整；"
            "A1 Snapshot 並非 A2 成交認證，供應商授權/資料語意另待證實"
        ),
        "session_date": verified_complete_session_date,
        "checked_at_tpe": stamp.astimezone(TPE).isoformat(),
        "capture_date_tpe": stamp.astimezone(TPE).date().isoformat(),
        "source_session_date": verified_complete_session_date,
        "universe_count": count,
        "run_id": integrity["run_id"],
        "run_attempt": integrity["run_attempt"],
        "head_sha": integrity["head_sha"],
        "artifact_id": integrity["artifact_id"],
        "verified_file_count": integrity["verified_file_count"],
        "research_markdown": markdown,
        "live_quote_certified": False,
        "new_entry_authorized": False,
        "production_eligible": False,
        "automatic_orders": False,
        "trade_action": "禁止交易",
    }
