from src import official


def test_explicit_last_trade_price_retained_but_not_certified(monkeypatch):
    def mock_snapshot(market):
        return {"date": "2026-11-10", "data": [
            {"symbol": "1234", "lastPrice": None,
             "lastTrade": {"price": 42.5}, "previousClose": 41,
             "tradeVolume": 1200}
        ] if market == "TSE" else []}
    monkeypatch.setattr("src.fugle.snapshot_quotes", mock_snapshot)
    rows, _ = official.fetch_fugle_snapshot_quotes(
        [{"symbol": "1234", "market": "TSE", "exchange": "TWSE"}],
        trading_date="2026-11-10")
    assert len(rows) == 1
    assert rows[0]["last"] == 42.5
    assert rows[0]["last_trade_timestamp"] is None


def test_closeprice_only_never_promoted(monkeypatch):
    def mock_snapshot(market):
        return {"date": "2026-11-10", "data": [
            {"symbol": "1234", "closePrice": 42.5, "previousClose": 41,
             "tradeVolume": 1200}
        ] if market == "TSE" else []}
    monkeypatch.setattr("src.fugle.snapshot_quotes", mock_snapshot)
    rows, _ = official.fetch_fugle_snapshot_quotes(
        [{"symbol": "1234", "market": "TSE", "exchange": "TWSE"}],
        trading_date="2026-11-10")
    assert rows == []
