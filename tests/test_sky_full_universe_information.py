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


def test_all_mandatory_columns_exist_in_every_stock():
    from research.sky_full_universe_information import REQUIRED_INFORMATION_COLUMNS
    report = build(U, {}, NOW)
    for row in report["all_symbols"]:
        detail = row["required_fields"]
        assert tuple(detail) == REQUIRED_INFORMATION_COLUMNS
        assert detail["即時價"] is None
        assert detail["最近觀察價（可能延遲）"] is None
        assert detail["買進觸發"] is None
        assert detail["多方評分"] is None
        assert detail["現在動作"] == "禁止交易"
    assert report["missing_field_label"] == "待確認（未有可驗證資料）"


def test_stale_observation_not_promoted_to_live_trade():
    old = NOW - timedelta(minutes=30)
    report = build(U, {"TSE": {"date": NOW.date().isoformat(), "data": [
        {"symbol": "1001", "lastPrice": 37.0, "lastTrade": {"time": old.isoformat()}}
    ]}}, NOW)
    row = report["all_symbols"][0]["required_fields"]
    assert row["最近觀察價（可能延遲）"] == 37.0
    assert row["即時價"] is None
    assert row["目標一"] is None
    assert row["最高接受價"] is None


def test_snapshot_without_lasttrade_time_keeps_reference_and_collection_clock():
    payload = {"TSE": {"date": NOW.date().isoformat(), "data": [
        {"symbol": "1001", "lastPrice": 33.5, "tradeVolume": 250,
         "lastUpdated": NOW.isoformat(), "closeTime": NOW.isoformat()}
    ]}}
    report = build(U, payload, NOW)
    row = report["all_symbols"][0]
    assert row["last_price"] == 33.5
    assert row["data_status"] == "UNVERIFIED_EXECUTION_TIME"
    assert row["last_trade_time"] is None
    assert row["snapshot_observed_at"] == NOW.isoformat()
    assert row["required_fields"]["資料時間"] == NOW.isoformat()
    assert row["required_fields"]["最近觀察價（可能延遲）"] == 33.5
    assert row["required_fields"]["即時價"] is None
    assert report["snapshot_reference_requires_last_trade_time"] is False
    assert report["snapshot_reference_without_trade_time_count"] == 1
    assert report["fresh_executed_count"] == 0
    assert report["no_order_or_production_promotion"] is True


def test_snapshot_integrity_distinguishes_missing_duplicates_and_no_trades():
    payload = {
        "TSE": {"date": NOW.date().isoformat(), "time": NOW.isoformat(), "data": [
            {"symbol": "1001", "lastPrice": 40, "tradeVolume": 0},
            {"symbol": "1001", "lastPrice": 40, "tradeVolume": 0},
            {"symbol": "9999", "lastPrice": 8},
        ]},
        "OTC": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "2001", "tradeVolume": 0},
        ]},
    }
    report = build(U, payload, NOW)
    twse = report["snapshot_integrity"]["TWSE"]
    tpex = report["snapshot_integrity"]["TPEx"]
    assert twse["api_response_valid"] is True
    assert twse["duplicate_symbol_rows"] == 1
    assert twse["unexpected_symbols"] == 1
    assert twse["official_symbol_coverage_pct"] == 100.0
    assert twse["snapshot_time_is_execution_time"] is False
    assert tpex["official_symbols_missing_from_snapshot"] == 1
    assert report["all_symbols"][1]["data_status"] == "MISSING_EXECUTED_PRICE"
    assert report["all_symbols"][1]["source"] == "Fugle paid bulk snapshot"
    assert report["snapshot_api_calls_expected_per_scan"] == 2
    assert report["fresh_executed_count"] == 0


def test_missing_snapshot_market_does_not_look_like_success():
    report = build(U, {"TSE": {"date": NOW.date().isoformat(), "data": []}}, NOW,
                   errors={"OTC": "HTTP_ERROR"})
    assert report["snapshot_integrity"]["TWSE"]["api_response_valid"] is True
    assert report["snapshot_integrity"]["TWSE"]["official_symbols_missing_from_snapshot"] == 1
    assert report["snapshot_integrity"]["TPEx"]["api_response_valid"] is False
    assert report["snapshot_integrity"]["TPEx"]["official_symbols_missing_from_snapshot"] == 2
    assert report["snapshot_errors"]["OTC"] == "HTTP_ERROR"
