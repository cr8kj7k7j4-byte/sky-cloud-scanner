import pytest

from src.research_sources import (
    SOURCE_REGISTRY,
    classify_event,
    normalize_record,
    source_health_template,
)


def test_official_source_priority_is_higher_than_media():
    assert SOURCE_REGISTRY["mops"].authority_rank > SOURCE_REGISTRY["media"].authority_rank


def test_normalize_record_keeps_traceability():
    item = normalize_record(
        symbol="2330",
        category="material_event",
        statement="重大訊息測試",
        source_key="mops",
        source_url="https://example.com",
        published_at="2026-10-24T10:00:00+08:00",
    )
    row = item.to_dict()
    assert row["source_type"] == "official"
    assert row["source_name"] == "公開資訊觀測站 MOPS"
    assert row["source_url"] == "https://example.com"


def test_unknown_source_is_rejected():
    with pytest.raises(KeyError):
        normalize_record(
            symbol="2330",
            category="news",
            statement="x",
            source_key="unknown_vendor",
        )


def test_event_classifier_does_not_create_trade_signal():
    result = classify_event("公司公告新產品正式量產並切入新客戶")
    assert "growth" in result["tags"]
    assert result["trade_signal"] is False


def test_source_health_starts_not_connected():
    health = source_health_template()
    assert health["mops"]["status"] == "NOT_CONNECTED"
