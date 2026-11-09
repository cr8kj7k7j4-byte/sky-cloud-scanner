from src.swing_live_scanner import _build_candidate, _swing_priority


def test_swing_priority_is_deterministic():
    row = {
        "change_pct": 2.0,
        "trade_value": 150_000_000,
        "last": 50.0,
        "high": 51.0,
        "low": 48.0,
        "open": 49.0,
    }
    assert _swing_priority(row) == _swing_priority(row)


def test_build_candidate_is_not_strategy_signal():
    row = {
        "symbol": "1234",
        "change_pct": 1.5,
        "trade_value": 100_000_000,
        "last": 40.0,
        "high": 41.0,
        "low": 39.0,
        "open": 39.5,
    }
    out = _build_candidate(row, 0.5, "swing5d")
    assert out["candidate_scope"] == "WHOLE_MARKET_OPERATIONAL_SCREEN"
    assert out["strategy_signal"] is False
    assert out["production_eligible"] is False


def test_partial_observations_stay_visible_but_not_tradable(monkeypatch, tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from src import swing_live_scanner as scanner
    from src.sky_mobile_table import normalize_mobile_row

    monkeypatch.setattr(scanner, "OUT", tmp_path)
    universe = [{"symbol": "1234", "exchange": "TWSE"}] * 10
    observed = [{
        "symbol": "1234", "name": "觀察樣本", "exchange": "TWSE",
        "last": 42.0, "open": 41.0, "high": 43.0, "low": 40.0,
        "change_pct": 2.0, "trade_value": 20000000, "volume": 1000
    }]
    monkeypatch.setattr(scanner, "load_official_universe", lambda: (universe, {"twse": 10, "tpex": 0}))
    monkeypatch.setattr(scanner, "fetch_fugle_snapshot_quotes", lambda *a, **kw: (observed, []))
    monkeypatch.setattr(scanner, "fetch_mis_quotes", lambda *a, **kw: ([], []))
    monkeypatch.setattr(scanner, "validate_whole_market_rows", lambda *a, **kw: {
        "accepted_rows": observed, "valid_whole_market_operational": False,
        "quote_scope": "PARTIAL_EXECUTED_LIVE", "by_exchange": {}
    })
    monkeypatch.setattr(scanner, "first_gate", lambda row: (True, []))
    monkeypatch.setattr(scanner, "get_ticker", lambda symbol: {})
    monkeypatch.setattr(scanner, "get_quote", lambda symbol: {})
    monkeypatch.setattr(scanner, "fugle_executed_trade", lambda *a, **kw: (None, None, "NO_VERIFIED_TRADE"))
    result = scanner.run("swing", top_n=10, deep_n=1)
    assert result["operational_full_market_scan"] is False
    assert result["candidate_count_scope"] == "PARTIAL_OBSERVED_SUBSET_ONLY"
    assert result["trade_eligibility"] == "NO_NEW_ENTRY_UNVERIFIED_COVERAGE"
    assert result["candidate_count"] == 1
    assert result["candidates"][0]["strategy_signal"] is False
    row = normalize_mobile_row(result["deep_candidates"][0])
    assert row["分類"] == "**X**"
    assert row["現在動作"] == "**觀察**"
    assert row["現價"] == "—"
    assert row["多方評分"] == "—"
    assert row["最高接受價"] == "—"
