"""Deterministic offline replay of 53 five-minute scan slots; not a market backtest."""
import json
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from .scan_history_archive import make_record

TW = timezone(timedelta(hours=8))


def replay_day(day="2026-11-06"):
    target = date.fromisoformat(day)
    if target.weekday() >= 5:
        raise ValueError("Select a weekday for the offline schedule replay")
    first = datetime(target.year, target.month, target.day, 9, 5, tzinfo=TW)
    slots = [first + timedelta(minutes=5 * index) for index in range(53)]
    records = []
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder, "latest.json")
        for index, slot in enumerate(slots):
            # This is intentionally a fixture, NOT an actual historical quote.
            path.write_text(json.dumps({
                "market_data_gate": "UNVERIFIED",
                "operational_full_market_scan": False,
                "quote_scope": "HISTORICAL_REPLAY_FIXTURE",
                "candidates": [],
            }), encoding="utf-8")
            record = make_record(folder, str(100000 + index), "1")
            record["scheduled_at_taipei"] = slot.isoformat()
            record["replay_only"] = True
            records.append(record)
    assert len(records) == 53
    assert len({r["run_id"] for r in records}) == 53
    assert all(r["status"] == "DATA_BLOCKED" and not r["production_signal"] for r in records)
    return {
        "schema": "SKY_SCAN_HISTORY_OFFLINE_REPLAY_V1",
        "date": day,
        "slots": len(records),
        "first": records[0]["scheduled_at_taipei"],
        "last": records[-1]["scheduled_at_taipei"],
        "all_unique": True,
        "status": "OFFLINE_FIXTURE_PASS",
        "live_market_verified": False,
        "gcs_write_verified": False,
        "mobile_deployment_verified": False,
    }


if __name__ == "__main__":
    print(json.dumps(replay_day(), ensure_ascii=False, indent=2))
