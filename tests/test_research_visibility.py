from src.research_visibility import build_research_visibility


def test_partial_feed_visible_but_cannot_trade():
    report = build_research_visibility(
        [{"symbol": "1101"}, {"symbol": "8088"}],
        [{"symbol": "1101", "exchange": "TWSE", "last": 37.0,
          "volume": 100, "trade_time": "2026-11-09T10:00:00+08:00"}],
        {"valid_whole_market_operational": False}, "2026-11-09T10:00:00+08:00")
    assert report["accepted_count"] == 1
    assert report["not_verified_count"] == 1
    assert report["quote_coverage_pct"] == 50.0
    assert report["production_signal"] is False
    assert report["order_authorized"] is False
    assert report["observations"][0]["research_direction"] is None
    assert report["observations"][0]["action"] == "觀察"


def test_no_accepted_quotes_never_fabricates_symbols():
    report = build_research_visibility([{"symbol": "1101"}], [], {}, "2026-11-09")
    assert report["observations"] == []
    assert report["accepted_count"] == 0
    assert report["trading_decision"] == "禁止新進場、未驗證通過"
