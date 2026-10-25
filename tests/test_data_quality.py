from datetime import datetime, timezone
import pandas as pd
from src.data_quality import assess_dataframe

def test_dq_pass_for_complete_fresh_frame():
    df = pd.DataFrame({
        "symbol": ["2409", "3481"],
        "timestamp": ["2026-10-25T01:30:00Z", "2026-10-25T01:31:00Z"],
        "price": [10.0, 20.0],
    })
    out = assess_dataframe(
        df,
        dataset="test",
        required_columns=["symbol", "timestamp", "price"],
        timestamp_column="timestamp",
        expected_rows=2,
        source_health="PASS",
        max_age_seconds=3600,
        now=datetime(2026, 10, 25, 1, 31, 30, tzinfo=timezone.utc),
    )
    assert out["status"] == "PASS"
    assert out["coverage"] == 1.0
    assert out["completeness"] == 1.0
    assert out["duplicates"] == 0
    assert out["timestamp_integrity"] == 1.0

def test_dq_fails_missing_required_column():
    df = pd.DataFrame({"symbol": ["2409"]})
    out = assess_dataframe(
        df, dataset="test", required_columns=["symbol", "price"], source_health="PASS"
    )
    assert out["status"] == "FAIL"
    assert out["missing_required_columns"] == ["price"]

def test_dq_blocks_bad_source():
    df = pd.DataFrame({"symbol": ["2409"]})
    out = assess_dataframe(
        df, dataset="test", required_columns=["symbol"], source_health="TRANSPORT_FAIL"
    )
    assert out["status"] == "BLOCKED"

def test_dq_warns_duplicates():
    df = pd.DataFrame({"symbol": ["2409", "2409"]})
    out = assess_dataframe(
        df, dataset="test", required_columns=["symbol"], source_health="PASS"
    )
    assert out["status"] == "WARN"
    assert out["duplicates"] == 1
