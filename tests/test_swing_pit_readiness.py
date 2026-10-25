import json

from research.validate_swing_pit_readiness import load_price_ranges


def test_daily_history_requires_adjustment_readiness(tmp_path):
    raw = {
        "symbol": "1111",
        "adjusted": False,
        "data": [{"date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1}],
    }
    capable = {
        "symbol": "2222",
        "adjusted": False,
        "adjustment_capability": "PIT_ASOF_EVENT_LEDGER",
        "data": [{"date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1}],
    }
    (tmp_path / "1111_D.json").write_text(json.dumps(raw), encoding="utf-8")
    (tmp_path / "2222_D.json").write_text(json.dumps(capable), encoding="utf-8")

    out = load_price_ranges(str(tmp_path))
    assert out["1111"]["adjustment_ready"] is False
    assert out["2222"]["adjustment_ready"] is True
