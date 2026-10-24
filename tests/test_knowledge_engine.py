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
