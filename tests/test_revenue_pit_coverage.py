import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.audit_revenue_pit_coverage import build_coverage_report


def test_missing_pit_blocks_promotion():
    revenue = [
        {"symbol":"2409","year":2025,"month":1,"market":"TWSE"},
        {"symbol":"3481","year":2025,"month":1,"market":"TWSE"},
    ]
    report = build_coverage_report(revenue, [], min_coverage_pct=100)
    assert report["coverage_pct"] == 0.0
    assert report["historical_pit_gate_pass"] is False
    assert report["promotion_allowed"] is False
    assert report["status"] == "PRE_PIT_CANDIDATE"


def test_only_official_verified_timestamps_count():
    revenue = [
        {"symbol":"2409","year":2025,"month":1,"market":"TWSE"},
        {"symbol":"3481","year":2025,"month":1,"market":"TWSE"},
    ]
    pit = [
        {
            "symbol":"2409",
            "revenue_year":2025,
            "revenue_month":1,
            "filing_published_at":"2025-02-10T17:00:00+08:00",
            "filing_timestamp_source":"MOPS_OFFICIAL",
            "point_in_time_verified":True,
        }
    ]
    report = build_coverage_report(revenue, pit, min_coverage_pct=100)
    assert report["covered_company_months"] == 1
    assert report["coverage_pct"] == 50.0
    assert report["historical_pit_gate_pass"] is False


def test_full_coverage_passes():
    revenue = [
        {"symbol":"2409","year":2025,"month":1,"market":"TWSE"},
    ]
    pit = [
        {
            "symbol":"2409",
            "revenue_year":2025,
            "revenue_month":1,
            "filing_published_at":"2025-02-10T17:00:00+08:00",
            "filing_timestamp_source":"MOPS_OFFICIAL",
            "point_in_time_verified":True,
        }
    ]
    report = build_coverage_report(revenue, pit, min_coverage_pct=100)
    assert report["coverage_pct"] == 100.0
    assert report["historical_pit_gate_pass"] is True
    assert report["promotion_allowed"] is True
