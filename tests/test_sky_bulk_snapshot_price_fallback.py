from src import official


def test_bulk_snapshot_can_preserve_lasttrade_price_without_freshness_claim(monkeypatch):
    def fake_snapshot(market):
        return {"date": "2026-11-10", "data": [
            {"symbol": "1234", "name": "測試", "lastPrice": None,
             "lastTrade": {"price": 42.5}, "previousClose": 41.0,
             "tradeVolume": 1200, "tradeValue": 51000000}
        ] if market == "TSE" else []}
    monkeypatch.setattr("src.fugle.snapshot_quotes", fake_snapshot)
    universe = [{"symbol": "1234", "market": "TSE",
                 "exchange": "TWSE", "name": "測試"}]
    rows, warnings = official.fetch_fugle_snapshot_quotes(universe, trading_date="2026-11-10")
    assert len(rows) == 1
    assert rows[0]["last"] == 42.5
    assert rows[0]["last_trade_timestamp"] is None
    assert rows[0]["quote_source"] == "Fugle bulk snapshot"


def test_bulk_snapshot_must_not_substitute_closeprice_for_trade(monkeypatch):
    def fake_snapshot(market):
        return {"date": "2026-11-10", "data": [
            {"symbol": "1234", "lastPrice": None,
             "closePrice": 42.5, "previousClose": 41.0,
             "tradeVolume": 1200}
        ] if market == "TSE" else []}
    monkeypatch.setattr("src.fugle.snapshot_quotes", fake_snapshot)
    rows, _ = official.fetch_fugle_snapshot_quotes(
        [{"symbol": "1234", "market": "TSE", "exchange": "TWSE"}],
        trading_date="2026-11-10")
    assert rows == []
