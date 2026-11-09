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

def test_partial_coverage_keeps_only_observed_rows(monkeypatch, tmp_path):
    from src import swing_live_scanner as scan
    monkeypatch.setattr(scan, "OUT", tmp_path)
    universe = [{"symbol": "1234", "exchange": "TWSE"}] * 20
    monkeypatch.setattr(scan, "load_official_universe", lambda: (universe, {"twse": 20, "tpex": 0}))
    row = {"symbol": "1234", "exchange": "TWSE", "last": 40.0, "open": 39.0,
           "high": 41.0, "low": 38.0, "change_pct": 2.0, "trade_value": 100_000_000}
    monkeypatch.setattr(scan, "fetch_fugle_snapshot_quotes", lambda *a, **kw: ([row], []))
    monkeypatch.setattr(scan, "fetch_mis_quotes", lambda *a, **kw: ([], []))
    monkeypatch.setattr(scan, "validate_whole_market_rows", lambda *a, **kw: {
        "accepted_rows": [row], "valid_whole_market_operational": False,
        "quote_scope": "PARTIAL_EXECUTED_LIVE"})
    monkeypatch.setattr(scan, "first_gate", lambda r: (True, []))
    monkeypatch.setattr(scan, "get_ticker", lambda _: {"limitUpPrice": 44.0})
    monkeypatch.setattr(scan, "get_quote", lambda _: {})
    monkeypatch.setattr(scan, "fugle_executed_trade", lambda *a, **kw: (None, None, "NO_FRESH_TRADE"))
    monkeypatch.setattr(scan, "render_mobile_table", lambda _: "觀察表")
    result = scan.run("swing5d")
    assert result["operational_full_market_scan"] is False
    assert result["observation_mode"] == "PARTIAL_SAMPLE_ONLY"
    assert result["candidate_count"] == 1
    assert result["candidates"][0]["candidate_scope"] == "PARTIAL_SAMPLE_OBSERVATION"
    assert result["candidates"][0]["relative_to_market_pct"] is None
    assert result["candidates"][0]["strategy_signal"] is False
    assert result["candidates"][0]["production_eligible"] is False
    assert result["deep_candidates"][0]["candidate_action"] == "等待"

def test_unverified_bulk_snapshot_is_visible_but_never_tradable(monkeypatch, tmp_path):
    from src import swing_live_scanner as scan
    monkeypatch.setattr(scan, "OUT", tmp_path)
    universe = [{"symbol": "1234", "exchange": "TWSE", "market": "TSE"}]
    row = {"symbol": "1234", "name": "研究樣本", "exchange": "TWSE",
           "quote_source": "Fugle bulk snapshot", "last": 45.0,
           "volume": 15000, "trade_value": 675000000, "quote_date": "2026-11-09",
           "quote_time": "2026-11-09T11:00:00+08:00", "last_trade_timestamp": None}
    monkeypatch.setattr(scan, "load_official_universe", lambda: (universe, {"twse": 1, "tpex": 0}))
    monkeypatch.setattr(scan, "fetch_fugle_snapshot_quotes", lambda *args, **kw: ([row], []))
    monkeypatch.setattr(scan, "fetch_mis_quotes", lambda *args, **kw: ([], []))
    monkeypatch.setattr(scan, "validate_whole_market_rows", lambda *args, **kw: {
        "accepted_rows": [], "valid_whole_market_operational": False,
        "quote_scope": "PARTIAL_EXECUTED_LIVE"})
    monkeypatch.setattr(scan, "render_mobile_table", lambda _: "")
    monkeypatch.setattr(scan, "get_quote", lambda _: {"date": "2026-11-09"})
    monkeypatch.setattr(scan, "fugle_executed_trade", lambda *a, **k: (None, None, "MISSING_EXECUTED_TRADE_TIME"))
    result = scan.run("swing5d")
    assert result["candidate_count"] == 0
    assert result["unverified_snapshot_observation_count"] == 1
    shown = result["unverified_snapshot_observations"][0]
    assert shown["indicative_last_price"] == 45.0
    assert shown["data_status"] == "UNVERIFIED_EXECUTED_TRADE_TIME"
    assert shown["strategy_signal"] is False
    assert shown["production_eligible"] is False
    assert shown["buy_trigger"] is None
    assert result["snapshot_coverage_pct"] == 100.0
    assert result["snapshot_exchange_counts"]["TWSE"] == 1
    import json
    artifact = json.loads((tmp_path / "snapshot_observations_swing5d.json").read_text())
    assert artifact["observed_symbols"] == 1
    assert artifact["data"][0]["strategy_signal"] is False
    assert result["snapshot_individual_verified_count"] == 0
    assert result["snapshot_individual_confirmation"][0]["data_status"] == "MISSING_EXECUTED_TRADE_TIME"
    assert result["snapshot_individual_confirmation"][0]["strategy_signal"] is False


def test_individually_confirmed_execution_remains_research_only(monkeypatch, tmp_path):
    from src import swing_live_scanner as scan
    from datetime import datetime
    monkeypatch.setattr(scan, "OUT", tmp_path)
    universe = [{"symbol": "1234", "exchange": "TWSE", "market": "TSE"}]
    sample = {"symbol": "1234", "name": "研究樣本", "exchange": "TWSE",
              "quote_source": "Fugle bulk snapshot", "last": 40.0,
              "volume": 1000, "trade_value": 40000000, "quote_date": "2026-11-09"}
    monkeypatch.setattr(scan, "load_official_universe", lambda: (universe, {"twse": 1, "tpex": 0}))
    monkeypatch.setattr(scan, "fetch_fugle_snapshot_quotes", lambda *a, **kw: ([sample], []))
    monkeypatch.setattr(scan, "fetch_mis_quotes", lambda *a, **kw: ([], []))
    monkeypatch.setattr(scan, "validate_whole_market_rows", lambda *a, **kw: {
        "accepted_rows": [], "valid_whole_market_operational": False,
        "quote_scope": "PARTIAL_EXECUTED_LIVE"})
    monkeypatch.setattr(scan, "render_mobile_table", lambda _: "")
    monkeypatch.setattr(scan, "get_quote", lambda _: {})
    monkeypatch.setattr(scan, "fugle_executed_trade",
                        lambda *a, **kw: (40.5, datetime.now(scan.TZ), "FRESH_EXECUTED_TRADE"))
    result = scan.run("swing5d")
    assert result["snapshot_individual_verified_count"] == 1
    x = result["snapshot_individual_confirmation"][0]
    assert x["verified_executed_price"] == 40.5
    assert x["verified_executed_at"] is not None
    assert x["strategy_signal"] is False
    assert x["production_eligible"] is False
    assert result["operational_full_market_scan"] is False
