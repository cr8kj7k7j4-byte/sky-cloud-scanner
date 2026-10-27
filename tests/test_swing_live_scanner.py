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
