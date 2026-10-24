import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.strategy_builder import build_breakout_plan, apply_plan


def candles():
    return {
        "data": [
            {"high": 10.0, "low": 9.8, "close": 9.9, "volume": 100},
            {"high": 10.1, "low": 9.85, "close": 10.0, "volume": 110},
            {"high": 10.2, "low": 9.9, "close": 10.1, "volume": 120},
            {"high": 10.15, "low": 9.95, "close": 10.1, "volume": 125},
            {"high": 10.25, "low": 10.0, "close": 10.2, "volume": 150},
        ]
    }


def test_build_plan():
    p = build_breakout_plan({"avg_price": 9.9}, candles())
    assert p is not None
    assert p.trigger == 10.2
    assert p.stop == 9.8
    assert p.target == 11.0
    assert p.max_entry == 10.3
    assert p.production_eligible is False


def test_requires_enough_bars():
    p = build_breakout_plan({}, {"data": candles()["data"][:3]})
    assert p is None


def test_vwap_guard():
    p = build_breakout_plan({"avg_price": 10.25}, candles())
    assert p is None


def test_apply_plan():
    p = build_breakout_plan({"avg_price": 9.9}, candles())
    c = apply_plan({"symbol": "2409"}, p)
    assert c["trigger"] == 10.2
    assert c["stop"] == 9.8
    assert c["target"] == 11.0
