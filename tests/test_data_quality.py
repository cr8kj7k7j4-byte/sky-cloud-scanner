from src.data_quality import evaluate_rows

def test_clean_rows_are_eligible():
    rows = [{
        "symbol":"2409","timestamp":"2026-10-25T01:00:00+00:00",
        "open":10,"high":11,"low":9,"close":10.5,"volume":100
    }]
    q = evaluate_rows(rows, observed_at="2026-10-25T01:00:10+00:00", freshness_seconds=60)
    assert q["decision_eligible"] is True
    assert q["freshness_ok"] is True

def test_duplicate_future_and_bad_tick_block():
    rows = [
        {"symbol":"2409","timestamp":"2026-10-25T01:01:00+00:00","open":10,"high":9,"low":8,"close":10,"volume":-1},
        {"symbol":"2409","timestamp":"2026-10-25T01:01:00+00:00","open":10,"high":11,"low":9,"close":10,"volume":1},
    ]
    q = evaluate_rows(rows, observed_at="2026-10-25T01:00:00+00:00", freshness_seconds=60)
    assert q["decision_eligible"] is False
    assert "duplicates" in q["errors"]
    assert "bad_ticks" in q["errors"]
    assert "timestamp_causality" in q["errors"]

def test_missing_required_blocks():
    q = evaluate_rows([{"symbol":"2409"}], observed_at="2026-10-25T01:00:00+00:00")
    assert "missing_data" in q["errors"]
