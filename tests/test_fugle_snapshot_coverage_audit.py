from datetime import datetime
from zoneinfo import ZoneInfo

from research.fugle_snapshot_coverage_audit import audit_snapshot


NOW = datetime(2026, 11, 9, 9, 25, tzinfo=ZoneInfo("Asia/Taipei"))
UNIVERSE = [
    {"symbol": "2330", "exchange": "TWSE"},
    {"symbol": "2317", "exchange": "TWSE"},
    {"symbol": "6488", "exchange": "TPEx"},
]


def test_membership_never_certifies_executed_trade():
    snapshots = {
        "TSE": {"date": "2026-11-09", "time": "092500", "data": [
            {"symbol": "2330", "lastPrice": 1000, "lastUpdated": 123},
            {"symbol": "2330", "lastPrice": 1000},
            {"symbol": "9999", "lastPrice": 1},
        ]},
        "OTC": {"date": "2026-11-09", "time": "092500", "data": [
            {"symbol": "6488", "lastPrice": 100},
        ]},
    }
    got = audit_snapshot(UNIVERSE, snapshots, NOW)
    assert got["markets"]["TSE"]["matched"] == 1
    assert got["markets"]["TSE"]["missing"] == 1
    assert got["markets"]["TSE"]["outside_universe"] == 1
    assert got["markets"]["TSE"]["duplicate_symbols"] == 1
    assert got["markets"]["TSE"]["symbol_coverage_pct"] == 50.0
    assert got["markets"]["OTC"]["symbol_coverage_pct"] == 100.0
    assert got["status"] == "BOTH_MARKETS_SYMBOL_SCOPE_OBSERVED"
    assert got["symbol_coverage_gate"] == "REVIEW_LOW_COVERAGE_OR_DUPLICATES"
    assert got["whole_market_live_certified"] is False
    assert got["trade_time_verified"] is False
    assert got["market_data_gate"] == "NO_TRADE"
    assert got["markets"]["TSE"]["executed_trade_coverage_pct"] is None


def test_stale_and_missing_fails_closed():
    got = audit_snapshot(
        UNIVERSE,
        {"TSE": {"date": "2026-11-06", "data": [{"symbol": "2330"}]}}, NOW,
    )
    assert got["status"] == "INSUFFICIENT_DATA"
    assert got["symbol_coverage_gate"] == "NOT_EVALUABLE"
    assert got["markets"]["TSE"]["status"] == "STALE_SNAPSHOT"
    assert got["markets"]["OTC"]["status"] == "SOURCE_UNAVAILABLE"
    assert got["whole_market_live_certified"] is False


def test_same_day_complete_universe_membership_pass_still_no_trade():
    got = audit_snapshot(UNIVERSE, {
        "TSE": {"date": "2026-11-09", "data": [{"symbol": "2330"}, {"symbol": "2317"}]},
        "OTC": {"date": "2026-11-09", "data": [{"symbol": "6488"}]},
    }, NOW)
    assert got["symbol_coverage_gate"] == "PASS_MEMBERSHIP_ONLY"
    assert got["market_data_gate"] == "NO_TRADE"
    assert got["whole_market_live_certified"] is False
