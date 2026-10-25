from src.monitor_engine import evaluate_monitor_state
from src.position_manager import evaluate_position


def test_monitor_uses_pms_effective_stop_when_widening_requested():
    c = {
        "symbol": "TEST",
        "holding": True,
        "last": 9.75,
        "cost": 10.0,
        "initial_stop": 9.8,
        "stop": 9.5,
        "target": 11.0,
        "risk": {"status": "ALLOW"},
    }
    p = evaluate_position(c)
    assert p.effective_stop == 9.8
    assert p.stop_widening_rejected is True

    m = evaluate_monitor_state(c)
    assert m.state == "STOP"
    assert m.stop == 9.8
    assert m.action == "停損"


def test_monitor_never_converts_losing_add_signal_to_add():
    c = {
        "symbol": "TEST",
        "holding": True,
        "last": 9.9,
        "cost": 10.0,
        "initial_stop": 9.5,
        "add_price": 9.8,
        "add_signal_confirmed": True,
        "risk": {"status": "ALLOW"},
    }
    p = evaluate_position(c)
    assert p.add_allowed is False
    m = evaluate_monitor_state(c)
    assert m.action != "加碼"


def test_monitor_can_surface_profitable_confirmed_add():
    c = {
        "symbol": "TEST",
        "holding": True,
        "last": 10.6,
        "cost": 10.0,
        "initial_stop": 9.8,
        "add_price": 10.5,
        "add_signal_confirmed": True,
        "risk": {"status": "ALLOW"},
    }
    p = evaluate_position(c)
    assert p.add_allowed is True
    m = evaluate_monitor_state(c)
    assert m.state == "ADD_READY"
    assert m.action == "加碼"
