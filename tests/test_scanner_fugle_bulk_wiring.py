"""Regression: paid bulk quotes join the existing executed-trade gate, not a shortcut."""
from datetime import datetime
from zoneinfo import ZoneInfo

from src import official
from src.realtime_quote_evidence import validate_whole_market_rows

NOW = datetime(2026, 11, 9, 11, 20, tzinfo=ZoneInfo("Asia/Taipei"))
UNIVERSE = [
    {"symbol": "1001", "exchange": "TWSE", "market": "TSE"},
    {"symbol": "2001", "exchange": "TPEx", "market": "OTC"},
]


def test_bulk_snapshot_rows_can_pass_only_with_fresh_executed_trade(monkeypatch):
    def snapshot(market):
        symbol = "1001" if market == "TSE" else "2001"
        return {"date": NOW.date().isoformat(), "data": [{
            "symbol": symbol, "lastPrice": 50, "previousClose": 49,
            "tradeVolume": 1000, "tradeValue": 50000000,
            "lastTrade": {"time": NOW.isoformat()},
        }]}

    monkeypatch.setattr("src.fugle.snapshot_quotes", snapshot)
    rows, warnings = official.fetch_fugle_snapshot_quotes(
        UNIVERSE, trading_date=NOW.date().isoformat())
    audit = validate_whole_market_rows(
        UNIVERSE, rows, now=NOW, min_coverage_pct=100,
        min_exchange_pct=100)
    assert len(rows) == 2
    assert audit["valid_quote_count"] == 2
    assert audit["valid_whole_market_operational"] is True


def test_bulk_snapshot_update_timestamp_does_not_count_as_trade(monkeypatch):
    def snapshot(market):
        symbol = "1001" if market == "TSE" else "2001"
        return {"date": NOW.date().isoformat(), "data": [{
            "symbol": symbol, "lastPrice": 50, "previousClose": 49,
            "tradeVolume": 1000, "lastUpdated": NOW.isoformat()
        }]}
    monkeypatch.setattr("src.fugle.snapshot_quotes", snapshot)
    rows, _ = official.fetch_fugle_snapshot_quotes(
        UNIVERSE, trading_date=NOW.date().isoformat())
    audit = validate_whole_market_rows(UNIVERSE, rows, now=NOW)
    assert audit["valid_quote_count"] == 0
    assert audit["valid_whole_market_operational"] is False
