from src.knowledge_engine import (
    Evidence,
    build_evidence_ledger,
    build_candidate_structured_ledger,
    build_news_evidence_ledger,
)
from src.evidence_ledger import build_evidence_ledger as legacy_candidate_ledger
from src.news_evidence import build_news_evidence_ledger as legacy_news_ledger


def test_candidate_adapter_matches_canonical_shape():
    candidate = {
        "symbol": "TEST",
        "last": 10.5,
        "change_pct": 1.2,
        "volume": 1000,
        "quote_time": "2026-10-25T09:30:00+08:00",
        "quote_source": "E2E",
        "relative_strength_score": 72.0,
    }
    canonical = build_candidate_structured_ledger(candidate, "2026-10-25T09:31:00+08:00")
    legacy = legacy_candidate_ledger(candidate, "2026-10-25T09:31:00+08:00")
    assert canonical == legacy
    assert canonical["fact_count"] >= 3
    assert canonical["derived_count"] == 1


def test_news_adapter_never_creates_trade_signal():
    rows = [{
        "subject": "測試新聞",
        "source_url": "https://example.com/a",
        "source": "example",
        "published_at": "2026-10-25T08:00:00+08:00",
        "source_tier": "media",
        "authority_score": 60,
        "affected_sectors": ["panel"],
    }]
    run_time = "2026-10-25T09:00:00+08:00"
    canonical = build_news_evidence_ledger(rows, run_time=run_time)
    legacy = legacy_news_ledger(rows, run_time=run_time)
    assert canonical == legacy
    assert canonical["record_count"] == 1
    assert canonical["records"][0]["trade_signal"] is False


def test_core_conflict_and_recency_contract_remains_canonical():
    a = Evidence("TEST", "event", "A", "official", "A")
    b = Evidence("TEST", "event", "B", "company", "B")
    ledger = build_evidence_ledger([a, b])
    assert ledger["conflict"] is True
    assert ledger["decision_eligible"] is False
