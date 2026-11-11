"""Independent, offline validation of a downloaded Sky Chat GitHub Artifact.

Runs after upload, on downloaded files only. Never calls Fugle or places orders.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.sky_chat_bridge import COLUMNS
from src.sky_scan_readback import validate_scan_readback


def verify_download(root: Path, *, run_id: str, request_id: str,
                    head_sha: str, expected_sha: str,
                    artifact_id: str, now: datetime | None = None) -> dict:
    if not (head_sha and expected_sha and head_sha == expected_sha):
        raise ValueError("RUN_HEAD_SHA_MISMATCH")
    if not artifact_id or not artifact_id.isdecimal():
        raise ValueError("ARTIFACT_ID_MISSING")
    status_file = root / "chat_bridge/latest.json"
    report_file = root / "sky_quickscan_information/latest_13col.json"
    status = json.loads(status_file.read_text(encoding="utf-8"))
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if not isinstance(status, dict) or status.get("head_sha") != expected_sha:
        raise ValueError("DOWNLOADED_STATUS_SHA_MISMATCH")
    attestation = validate_scan_readback(
        status, expected_run_id=run_id, expected_request_id=request_id,
        now=now or datetime.now(timezone.utc),
    )
    if report.get("schema") != "SKY_DAYTRADE_13COL_RESEARCH_V2":
        raise ValueError("REPORT_SCHEMA_INVALID")
    # Cross-check the two independently downloaded files, not just each alone.
    # Both timestamps are Snapshot capture times, NOT executed-trade times.
    if report.get("checked_at_tpe") != status.get("data_timestamp"):
        raise ValueError("REPORT_CAPTURE_TIMESTAMP_MISMATCH")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != report.get("row_count"):
        raise ValueError("REPORT_ROWS_INVALID")
    if (not rows or len(rows) != status.get("row_count")
            or report.get("universe_count") != len(rows)):
        raise ValueError("REPORT_COUNT_MISMATCH")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or any(col not in row for col in COLUMNS):
            raise ValueError("REPORT_MISSING_13_COLUMNS")
        symbol = str(row.get("股票代碼") or "")
        if not symbol or symbol in seen:
            raise ValueError("REPORT_DUPLICATE_OR_MISSING_SYMBOL")
        seen.add(symbol)
        if row.get("正式交易資格") is not False or row.get("現在動作") in ("買進", "加碼"):
            raise ValueError("REPORT_TRADE_GATE_VIOLATION")
    if report.get("production_eligible") is not False:
        raise ValueError("REPORT_PRODUCTION_ELIGIBLE")
    return {
        "schema": "SKY_CHAT_EXTERNAL_ARTIFACT_READBACK_V1",
        "status": "PASS_RESEARCH_ONLY",
        "run_id": run_id, "head_sha": head_sha, "request_id": request_id,
        "artifact_id": artifact_id, "row_count": len(rows),
        "snapshot_capture_at": attestation["snapshot_capture_at"],
        "verified_executed_count": attestation["stage2_verified_executed_count"],
        "production_eligible": False, "automatic_order": False,
        "trade_action": "禁止交易",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for field in ("directory", "run-id", "request-id", "head-sha", "expected-sha", "artifact-id"):
        parser.add_argument("--" + field, required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    target = Path(args.receipt)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        receipt = verify_download(Path(args.directory), run_id=args.run_id,
                                  request_id=args.request_id, head_sha=args.head_sha,
                                  expected_sha=args.expected_sha, artifact_id=args.artifact_id)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        receipt = {"schema": "SKY_CHAT_EXTERNAL_ARTIFACT_READBACK_V1",
                   "status": "FAILED_CLOSED", "reason": str(exc)[:160],
                   "run_id": args.run_id, "head_sha": args.head_sha,
                   "request_id": args.request_id,
                   "production_eligible": False, "automatic_order": False,
                   "trade_action": "禁止交易"}
        target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise SystemExit("EXTERNAL_ARTIFACT_READBACK_FAILED") from exc
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
