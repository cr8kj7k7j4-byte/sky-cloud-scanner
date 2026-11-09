from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.sky_full_universe_information import build, record, summary

NOW = datetime(2026, 11, 9, 11, 30, tzinfo=ZoneInfo("Asia/Taipei"))
U = [
    {"symbol": "1001", "name": "A", "exchange": "TWSE"},
    {"symbol": "2001", "name": "B", "exchange": "TPEx"},
    {"symbol": "2002", "name": "C", "exchange": "TPEx"},
]


def test_all_symbols_preserved_and_info_visible_despite_trade_block():
    snapshots = {
        "TSE": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "1001", "lastPrice": 43, "previousClose": 40,
             "tradeVolume": 1000, "lastTrade": {"time": NOW.isoformat()}}]},
        "OTC": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "2001", "lastPrice": 23, "previousClose": 22,
             "tradeVolume": 500, "lastUpdated": NOW.isoformat()}]},
    }
    report = build(U, snapshots, NOW)
    assert len(report["all_symbols"]) == 3
    assert report["observed_price_count"] == 2
    assert report["fresh_executed_count"] == 1
    assert report["by_exchange"]["TPEx"]["fresh_executed"] == 0
    assert report["trade_decision"].startswith("🔴")
    assert report["ranked_observations"][0]["symbol"] == "1001"
    assert report["all_symbols"][1]["data_status"] == "UNVERIFIED_EXECUTION_TIME"
    assert report["all_symbols"][2]["data_status"] == "MISSING_QUOTE"
    assert "禁止新進場" in summary(report)


def test_stale_timestamp_disclosed_without_production_promotion():
    meta = U[0]
    row = record(meta, {
        "lastPrice": 99, "previousClose": 98,
        "lastTrade": {"time": (NOW - timedelta(minutes=20)).isoformat()},
    }, NOW.date().isoformat(), NOW)
    assert row["last_price"] == 99
    assert row["data_status"] == "STALE_EXECUTION_TIME"
    assert row["production_eligible"] is False
    assert row["trade_signal"] is False


def test_snapshot_old_date_cannot_be_fresh_even_if_trade_clock_is_recent():
    row = record(U[0], {"lastPrice": 80, "lastTrade": {"time": NOW.isoformat()}},
                 "2026-11-06", NOW)
    assert row["data_status"] == "SNAPSHOT_DATE_NOT_TODAY"


def test_zero_price_or_missing_market_is_not_fabricated():
    row = record(U[1], {"lastPrice": 0, "lastUpdated": NOW.isoformat()},
                 NOW.date().isoformat(), NOW)
    assert row["last_price"] is None
    report = build(U, {}, NOW)
    assert report["observed_price_count"] == 0
    assert len(report["all_symbols"]) == 3
    assert report["ranked_observations"] == []
