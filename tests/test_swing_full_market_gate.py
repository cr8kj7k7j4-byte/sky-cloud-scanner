from datetime import datetime
from zoneinfo import ZoneInfo

from src import swing_live_scanner as swing

TZ = ZoneInfo("Asia/Taipei")


def test_incomplete_broad_market_quotes_are_blocked_before_any_fugle_deep_dive(monkeypatch, tmp_path):
    monkeypatch.setattr(swing, "OUT", tmp_path)
    pool = [{"symbol": "1001", "exchange": "TWSE"}] + [
        {"symbol": str(i), "exchange": "TPEx"} for i in range(2001, 2005)
    ]
    monkeypatch.setattr(swing, "load_official_universe", lambda: (
        pool, {"twse": 1, "tpex": 4, "warnings": []}
    ))
    monkeypatch.setattr(swing, "fetch_fugle_snapshot_quotes", lambda *a, **kw: ([], []))
    def no_deep(*args, **kwargs):
        raise AssertionError("Invalid market must never call candidate deep dive")
    monkeypatch.setattr(swing, "get_ticker", no_deep)
    monkeypatch.setattr(swing, "get_quote", no_deep)
    result = swing.run("swing5d")
    assert result["market_data_gate"] == "BLOCKED_EXTERNAL_DATA_NO_TRADE"
    assert result["operational_full_market_scan"] is False
    assert result["candidate_count"] == 0
    assert result["deep_candidates"] == []
    assert result["live_market_evidence"]["valid_quote_count"] == 0
