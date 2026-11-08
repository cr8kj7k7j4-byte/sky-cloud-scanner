"""Governance-stage regression: two consecutive stops must deny new entries."""
from src.risk_engine import RiskPolicy, evaluate_trade


def _decision(streak):
    return evaluate_trade(
        entry=50, stop=48, target=55, account_equity=500000,
        daily_pnl=0, open_risk=0, concurrent_positions=0,
        consecutive_losses=streak, grade="A+",
        policy=RiskPolicy(lot_size=1000, risk_per_trade_pct=0.01,
                          daily_loss_limit_pct=0.02),
    )


def test_first_loss_does_not_trigger_two_loss_kill_switch():
    result=_decision(1)
    assert result["status"] == "ALLOW"
    assert result["recommended_shares"] > 0


def test_second_loss_blocks_even_a_plus():
    result=_decision(2)
    assert result["status"] == "BLOCK"
    assert result["recommended_shares"] == 0
    assert result["portfolio_allowed"] is False
    assert any("連續兩筆停損" in text for text in result["reasons"])


def test_three_losses_remains_blocked():
    assert _decision(3)["status"] == "BLOCK"


def test_confirmed_p0r_cash_limits():
    policy = RiskPolicy(
        risk_per_trade_pct=0.01, daily_loss_limit_pct=0.02,
        max_portfolio_heat_pct=0.03, max_position_pct=0.20,
        max_concurrent_positions=3, lot_size=1000,
    )
    params = dict(entry=50, stop=48, target=55,
                  account_equity=500000, grade="A+", policy=policy)
    normal = evaluate_trade(**params, consecutive_losses=0)
    assert normal["status"] == "ALLOW"
    assert normal["risk_budget"] == 5000
    assert normal["recommended_shares"] == 2000
    assert normal["proposed_risk"] == 4000
    assert normal["remaining_portfolio_heat"] == 15000
    assert evaluate_trade(**params, daily_pnl=-10000)["status"] == "BLOCK"
    assert evaluate_trade(**params, open_risk=15000)["status"] == "BLOCK"
    assert evaluate_trade(**params, concurrent_positions=3)["status"] == "BLOCK"
    assert evaluate_trade(**params, consecutive_losses=2)["status"] == "BLOCK"


def test_cost_assumptions_are_not_conflated_with_net_rr():
    result = _decision(0)
    assert result["execution_status"] == "EXECUTION_INPUT_REQUIRED"
    assert result["execution_adjusted_rr"] is None
    # P0-R arithmetic is not a proven production entry permit.


def test_long_stop_cannot_be_at_or_above_entry():
    params = dict(entry=50, target=55, account_equity=500000,
                  policy=RiskPolicy(risk_per_trade_pct=0.01, lot_size=1000))
    for invalid_stop in (50, 51):
        result = evaluate_trade(stop=invalid_stop, **params)
        assert result["status"] == "BLOCK"
        assert result["recommended_shares"] == 0
        assert any("做多停損必須低於買進價" in text for text in result["reasons"])


def test_execution_gate_default_requires_cost_inputs():
    import os
    import subprocess
    import sys
    env = dict(os.environ)
    env.pop("EXEC_ENFORCE_GATE", None)
    program = "from src.config import EXEC_ENFORCE_GATE; print(int(EXEC_ENFORCE_GATE))"
    completed = subprocess.run([sys.executable, "-c", program],
                               capture_output=True, text=True, env=env, check=True)
    assert completed.stdout.strip() == "1"


def test_unknown_execution_cost_blocks_risk_entry_when_gate_is_enabled():
    from src.execution_engine import ExecutionCostPolicy
    result = evaluate_trade(
        entry=50, stop=48, target=55, account_equity=500000,
        policy=RiskPolicy(risk_per_trade_pct=0.01),
        execution_policy=ExecutionCostPolicy(enforce_gate=True),
    )
    assert result["status"] == "BLOCK"
    assert result["recommended_shares"] == 0
    assert result["execution_status"] == "EXECUTION_INPUT_REQUIRED"
