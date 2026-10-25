from src.source_health import evaluate_source_health

def test_fresh_source_is_healthy():
    h=evaluate_source_health(source="TWSE",observed_at="2026-10-25T01:00:10+00:00",source_timestamp="2026-10-25T01:00:00+00:00",freshness_sla_seconds=30,record_count=1000,minimum_record_count=500)
    assert h["ok"] is True

def test_stale_or_future_source_degrades():
    stale=evaluate_source_health(source="TWSE",observed_at="2026-10-25T01:01:00+00:00",source_timestamp="2026-10-25T01:00:00+00:00",freshness_sla_seconds=30)
    future=evaluate_source_health(source="TWSE",observed_at="2026-10-25T01:00:00+00:00",source_timestamp="2026-10-25T01:00:01+00:00",freshness_sla_seconds=30)
    assert "stale_source" in stale["reasons"]
    assert "future_source_timestamp" in future["reasons"]
