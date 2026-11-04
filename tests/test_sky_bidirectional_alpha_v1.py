from datetime import datetime
from zoneinfo import ZoneInfo
from research.sky_bidirectional_alpha_v1 import classify_observations, run

def test_watchlists_never_emit_trade_signals():
    rows = [
        {"symbol": "1111", "exchange": "TWSE", "price": 50, "change_pct": 3, "trade_value": 20000000},
        {"symbol": "2222", "exchange": "TPEx", "price": 45, "change_pct": -4, "trade_value": 20000000},
        {"symbol": "3333", "exchange": "TWSE", "price": 150, "change_pct": 10, "trade_value": 20000000},
    ]
    long_rows, short_rows = classify_observations(rows, current_session=True, coverage_ok=True)
    assert [r["symbol"] for r in long_rows] == ["1111"]
    assert [r["symbol"] for r in short_rows] == ["2222"]
    for r in long_rows + short_rows:
        assert r["action"] == "觀察"
        assert r["entry_trigger"] is None and r["short_score"] is None
        assert r["stop"] is None and r["net_rr"] is None

def test_no_coverage_no_watchlist():
    rows = [{"symbol": "1111", "price": 50, "change_pct": 3, "trade_value": 20000000}]
    assert classify_observations(rows, current_session=True, coverage_ok=False) == ([], [])

def test_preopen_never_requests_market_data():
    report = run(datetime(2026, 11, 5, 8, 30, tzinfo=ZoneInfo("Asia/Taipei")))
    assert report["status"] == "BLOCKED_NO_TRADE"
    assert report["reason"] == "OUTSIDE_REGULAR_TAIWAN_STOCK_SESSION"
    assert report["long_watch"] == [] and report["short_watch"] == []
