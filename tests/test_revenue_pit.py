import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.revenue_pit import normalize_mops_published_at, revenue_pit_gate


def test_normalizes_roc_mops_timestamp():
    assert normalize_mops_published_at("115/10/21 17:43") == "2026-10-21T17:43:00+08:00"


def test_time_only_is_not_sufficient_for_pit():
    assert normalize_mops_published_at("17:43") is None


def test_pit_gate_requires_official_mops_source():
    ok = revenue_pit_gate({
        "filing_published_at": "2026-10-21T17:43:00+08:00",
        "filing_timestamp_source": "MOPS_OFFICIAL",
    })
    assert ok["point_in_time_verified"] is True
    assert ok["promotion_allowed"] is True

    proxy = revenue_pit_gate({
        "filing_published_at": "2026-10-21T17:43:00+08:00",
        "filing_timestamp_source": "DEADLINE_PROXY",
    })
    assert proxy["point_in_time_verified"] is False
    assert proxy["promotion_allowed"] is False
