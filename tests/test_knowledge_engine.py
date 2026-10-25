from datetime import datetime, timezone

from src.knowledge_engine import Evidence, build_evidence_ledger


def test_ledger_blocks_stale_evidence():
    item = Evidence(
        symbol="2330",
        category="news",
        statement="test",
        source_type="official",
        source_name="official",
        published_at="2026-10-20T00:00:00+00:00",
    )
    now = datetime(2026, 10, 24, tzinfo=timezone.utc)
    ledger = build_evidence_ledger([item], max_age_hours=24, now=now)
    assert ledger["stale_count"] == 1
    assert ledger["decision_eligible"] is False


def test_ledger_detects_conflicts():
    a = Evidence("2330", "event", "A", "official", "A")
    b = Evidence("2330", "event", "B", "company", "B")
    ledger = build_evidence_ledger([a, b])
    assert ledger["conflict"] is True
    assert ledger["decision_eligible"] is False


def test_evidence_preserves_provenance_fields():
    item = Evidence(
        symbol="2330",
        category="financial",
        statement="monthly revenue filed",
        source_type="official",
        source_name="MOPS",
        published_at="2026-10-25T08:00:00+08:00",
        observed_at="2026-10-25T08:01:00+08:00",
        ingestion_at="2026-10-25T08:02:00+08:00",
        company="TSMC",
        event_type="monthly_revenue",
        reliability=1.0,
        confidence=1.0,
        status="FACT",
    )
    row = item.to_dict()
    assert row["ingestion_at"] == "2026-10-25T08:02:00+08:00"
    assert row["company"] == "TSMC"
    assert row["event_type"] == "monthly_revenue"
    assert row["reliability"] == 1.0
    assert row["status"] == "FACT"
