"""Append-only scan history: never infer successful live quotes from a workflow result."""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TW = timezone(timedelta(hours=8))


def make_record(output_dir="output", run_id=None, run_attempt=None):
    folder = Path(output_dir)
    result_path = folder / "latest.json"
    trigger_path = folder / "schedule_trigger.json"
    record = {
        "schema": "SKY_SCAN_HISTORY_V1",
        "run_id": str(run_id or os.getenv("GITHUB_RUN_ID", "")),
        "run_attempt": str(run_attempt or os.getenv("GITHUB_RUN_ATTEMPT", "")),
        "completed_at_taipei": datetime.now(TW).isoformat(),
        "scheduled_at_taipei": None,
        "status": "DATA_BLOCKED",
        "market_data_gate": "UNVERIFIED",
        "quote_coverage_pct": None,
        "candidate_count": None,
        "candidates": [],
        "production_signal": False,
    }
    if trigger_path.is_file():
        try:
            trigger = json.loads(trigger_path.read_text(encoding="utf-8"))
            record["event_schedule_cron_utc"] = trigger.get("event_schedule_cron_utc")
            record["job_started_at_utc"] = trigger.get("job_started_at_utc")
        except (ValueError, OSError):
            pass
    if result_path.is_file():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if not isinstance(result, dict):
                raise ValueError("latest.json is not a JSON object")
            record["market_data_gate"] = result.get("market_data_gate") or "UNVERIFIED"
            record["quote_coverage_pct"] = result.get("quote_coverage_pct")
            candidates = result.get("candidates")
            if isinstance(candidates, list):
                record["candidate_count"] = len(candidates)
                # Snapshot only; do not invent prices or a validated signal.
                record["candidates"] = candidates[:100]
            if (result.get("operational_full_market_scan") is True
                and (result.get("live_market_evidence") or {}).get("valid_whole_market_operational") is True
                and result.get("quote_scope") == "WHOLE_MARKET_EXECUTED_LIVE"
                and record["market_data_gate"] == "PASS_FULL_MARKET_LIVE"):
                record["status"] = "MARKET_DATA_VERIFIED"
        except (ValueError, OSError, TypeError):
            record["status"] = "DATA_BLOCKED"
    return record


def save_record(record, bucket, prefix="scan-history"):
    if not bucket:
        raise ValueError("SKY_SCAN_HISTORY_BUCKET is not configured")
    from google.cloud import storage
    client = storage.Client()
    # Run ID + attempt prevents overwrites; UTC sortable prefix for latest-first listing.
    now = datetime.now(timezone.utc)
    key = (prefix.strip("/") + "/" + now.strftime("%Y/%m/%d/%H%M%S") +
           "_" + record["run_id"] + "_" + record["run_attempt"] + ".json")
    blob = client.bucket(bucket).blob(key)
    blob.upload_from_string(
        json.dumps(record, ensure_ascii=False, sort_keys=True),
        content_type="application/json",
        if_generation_match=0,
    )
    return key


def main():
    record = make_record()
    Path("output").mkdir(exist_ok=True)
    Path("output/scan_history_record.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bucket = os.getenv("SKY_SCAN_HISTORY_BUCKET", "").strip()
    if not bucket:
        print("BLOCKED: SKY_SCAN_HISTORY_BUCKET unset; local artifact retained")
        return 2
    try:
        print("GCS create-only:", save_record(record, bucket, os.getenv("SKY_SCAN_HISTORY_PREFIX", "scan-history")))
        return 0
    except Exception as exc:
        print("BLOCKED: GCS history write failed:", type(exc).__name__)
        return 2


if __name__ == "__main__":
    sys.exit(main())
