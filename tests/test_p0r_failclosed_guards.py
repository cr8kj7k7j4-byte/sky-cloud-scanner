from src.risk_engine import RiskPolicy, evaluate_trade, evaluate_candidate
from src.position_manager import evaluate_position


def test_policy_matches_p0r_profile():
    p = RiskPolicy()
    assert 500000 * p.risk_per_trade_pct == 5000
    assert 500000 * p.daily_loss_limit_pct == 10000
    assert 500000 * p.max_portfolio_heat_pct == 15000
    assert 500000 * p.max_position_pct == 100000
    assert p.max_concurrent_positions == 3


def test_two_losses_lock_even_without_daily_limit():
    decision = evaluate_trade(entry=50, stop=48, target=54, account_equity=500000,
                              consecutive_losses=2, policy=RiskPolicy())
    assert decision["status"] == "BLOCK"
    assert decision["recommended_shares"] == 0


def test_long_stop_cannot_be_above_entry():
    decision = evaluate_trade(entry=50, stop=51, target=54, account_equity=500000)
    assert decision["status"] == "BLOCK"


def test_missing_verified_portfolio_cannot_size():
    result = evaluate_candidate({"entry": 50, "stop": 48, "target": 55}, {"account_equity": 500000})
    assert result["status"] == "RISK_INPUT_REQUIRED"
    assert result["recommended_shares"] == 0


def test_missing_cost_or_stop_cannot_add():
    base = {"symbol": "TEST", "last": 12, "cost": 10, "initial_stop": 9,
            "add_price": 11, "add_signal_confirmed": True, "risk": {"status": "ALLOW"}}
    for field in ("cost", "initial_stop", "add_price"):
        case = dict(base)
        case.pop(field)
        decision = evaluate_position(case)
        assert decision.add_allowed is False, field
    case = dict(base)
    case["risk"] = {}
    assert evaluate_position(case).add_allowed is False


def test_lose_money_cannot_add_or_widen_stop():
    case = {"symbol": "TEST", "last": 9.8, "cost": 10, "initial_stop": 9,
            "stop": 8, "add_price": 9.5, "add_signal_confirmed": True,
            "risk": {"status": "ALLOW"}}
    decision = evaluate_position(case)
    assert decision.stop_widening_rejected
    assert decision.effective_stop == 9
    assert decision.add_allowed is False


def test_daily_boundary_blocks():
    decision = evaluate_trade(entry=50, stop=48, target=54, account_equity=500000,
                              daily_pnl=-10000)
    assert decision["status"] == "BLOCK"

def test_candidate_requires_complete_cost_gate_and_no_real_order():
    from src.execution_engine import ExecutionCostPolicy
    context = {"account_equity": 500000, "daily_pnl": 0, "open_risk": 0,
               "concurrent_positions": 0, "consecutive_losses": 0,
               "positions_verified": True,
               "execution_policy": ExecutionCostPolicy(enforce_gate=False)}
    result = evaluate_candidate({"entry": 50, "stop": 49, "target": 52}, context)
    assert result["status"] == "BLOCK"
    assert result["recommended_shares"] == 0
    assert result["execution_status"] == "EXECUTION_INPUT_REQUIRED"


def test_reaching_target_does_not_allow_add():
    case = {"symbol": "TEST", "last": 12, "cost": 10, "initial_stop": 9,
            "target": 12, "add_price": 11, "add_signal_confirmed": True,
            "risk": {"status": "ALLOW"}}
    decision = evaluate_position(case)
    assert decision.state == "TAKE_PROFIT"
    assert decision.add_allowed is False

def test_paper_only_does_not_require_broker_account():
    from src.execution_engine import ExecutionCostPolicy
    from src.cost_profiles import USER_CASH_DAYTRADE_20261022
    cost = USER_CASH_DAYTRADE_20261022.to_execution_policy(
        entry_slippage_bps=5, exit_slippage_bps=5, spread_bps=10,
        liquidity_penalty_bps=2, enforce_gate=True)
    paper_ledger = {"mode": "PAPER_ONLY", "daily_realized_net_pnl_twd": 0,
                    "consecutive_stops": 0, "open_positions": 0,
                    "open_stop_risk_twd": 0}
    ctx = {"mode": "PAPER_ONLY", "paper_ledger": paper_ledger,
           "account_equity": 500000, "daily_pnl": 0, "open_risk": 0,
           "concurrent_positions": 0, "consecutive_losses": 0,
           "execution_policy": cost}
    result = evaluate_candidate({"entry": 50, "stop": 49, "target": 53}, ctx)
    assert result["status"] == "ALLOW"
    assert result["portfolio_allowed"] is True


def test_paper_only_missing_or_mismatched_ledger_fails_closed():
    from src.execution_engine import ExecutionCostPolicy
    ctx = {"mode": "PAPER_ONLY", "account_equity": 500000, "daily_pnl": 0,
           "open_risk": 0, "concurrent_positions": 0, "consecutive_losses": 0,
           "execution_policy": ExecutionCostPolicy()}
    assert evaluate_candidate({"entry": 50, "stop": 49, "target": 53}, ctx)["recommended_shares"] == 0
    ctx["paper_ledger"] = {"mode": "PAPER_ONLY", "daily_realized_net_pnl_twd": -10000,
                           "consecutive_stops": 0, "open_positions": 0,
                           "open_stop_risk_twd": 0}
    assert evaluate_candidate({"entry": 50, "stop": 49, "target": 53}, ctx)["status"] == "RISK_INPUT_REQUIRED"
