import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.monitor_engine import evaluate_monitor_state


def test_watch_without_trigger():
    d = evaluate_monitor_state({"symbol": "2409", "last": 37.0})
    assert d.state == "WATCH"


def test_near_trigger():
    d = evaluate_monitor_state({"symbol": "2409", "last": 36.9, "trigger": 37.0})
    assert d.state == "NEAR_TRIGGER"


def test_triggered_requires_risk_or_pending_confirmation():
    d = evaluate_monitor_state(
        {"symbol": "2409", "last": 37.1, "trigger": 37.0, "risk": {"status": "ALLOW"}}
    )
    assert d.state == "TRIGGERED"
    assert d.action == "等待"


def test_anti_chase_invalidates_entry():
    d = evaluate_monitor_state(
        {"symbol": "2409", "last": 38.1, "trigger": 37.0, "max_entry": 38.0}
    )
    assert d.state == "INVALIDATED"
    assert d.action == "禁止交易"


def test_position_stop_has_priority():
    d = evaluate_monitor_state(
        {
            "symbol": "2409",
            "last": 35.9,
            "holding": True,
            "stop": 36.0,
            "target": 40.0,
        }
    )
    assert d.state == "STOP"
    assert d.action == "停損"


def test_position_target():
    d = evaluate_monitor_state(
        {
            "symbol": "2409",
            "last": 40.0,
            "holding": True,
            "stop": 36.0,
            "target": 40.0,
        }
    )
    assert d.state == "TAKE_PROFIT"


def test_risk_block_overrides_trigger():
    d = evaluate_monitor_state(
        {
            "symbol": "2409",
            "last": 37.2,
            "trigger": 37.0,
            "risk": {"status": "BLOCK", "reasons": ["Daily Loss Limit"]},
        }
    )
    assert d.state == "BLOCKED"


def test_changed_state():
    d = evaluate_monitor_state(
        {"symbol": "2409", "last": 36.9, "trigger": 37.0},
        previous_state="WATCH",
    )
    assert d.changed is True
    assert d.previous_state == "WATCH"
