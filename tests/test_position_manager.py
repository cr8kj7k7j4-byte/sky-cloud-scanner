from src.position_manager import evaluate_position


def test_stop_cannot_be_widened():
    c = {
        "symbol": "TEST",
        "last": 10.2,
        "cost": 10.0,
        "initial_stop": 9.8,
        "stop": 9.5,
        "target": 11.0,
        "risk": {"status": "ALLOW"},
    }
    d = evaluate_position(c).to_dict()
    assert d["effective_stop"] == 9.8
    assert d["stop_widening_rejected"] is True
    assert "拒絕" in d["reason"]


def test_losing_position_cannot_add():
    c = {
        "symbol": "TEST",
        "last": 9.8,
        "cost": 10.0,
        "initial_stop": 9.5,
        "add_price": 9.7,
        "add_signal_confirmed": True,
        "risk": {"status": "ALLOW"},
    }
    d = evaluate_position(c).to_dict()
    assert d["add_allowed"] is False
    assert d["action"] != "加碼"
    assert "禁止向下攤平" in d["reason"]


def test_profitable_confirmed_add_can_be_ready():
    c = {
        "symbol": "TEST",
        "last": 10.6,
        "cost": 10.0,
        "initial_stop": 9.8,
        "add_price": 10.5,
        "add_signal_confirmed": True,
        "risk": {"status": "ALLOW"},
    }
    d = evaluate_position(c).to_dict()
    assert d["state"] == "ADD_READY"
    assert d["action"] == "加碼"
    assert d["add_allowed"] is True


def test_stop_and_target_have_priority_over_add():
    stop_case = {
        "symbol": "TEST",
        "last": 9.7,
        "cost": 10.0,
        "initial_stop": 9.8,
        "add_signal_confirmed": True,
        "risk": {"status": "ALLOW"},
    }
    assert evaluate_position(stop_case).state == "STOP"

    target_case = {
        "symbol": "TEST",
        "last": 11.0,
        "cost": 10.0,
        "initial_stop": 9.8,
        "target": 11.0,
        "add_signal_confirmed": True,
        "risk": {"status": "ALLOW"},
    }
    assert evaluate_position(target_case).state == "TAKE_PROFIT"


def test_thesis_invalid_means_exit():
    d = evaluate_position({
        "symbol": "TEST",
        "last": 10.2,
        "cost": 10.0,
        "initial_stop": 9.8,
        "thesis_invalid": True,
    }).to_dict()
    assert d["state"] == "EXIT"
    assert d["action"] == "退出"
    assert d["thesis_valid"] is False
