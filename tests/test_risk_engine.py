import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.risk_engine import RiskPolicy, drawdown_state, evaluate_trade


def main():
    p = RiskPolicy(lot_size=1000)

    assert drawdown_state(0, 0, p) == "NORMAL"
    assert drawdown_state(0, 3, p) == "CAUTION"
    assert drawdown_state(0, 5, p) == "DEFENSIVE"
    assert drawdown_state(0.06, 0, p) == "LOCKDOWN"

    missing = evaluate_trade(
        entry=50,
        stop=None,
        target=None,
        account_equity=500000,
        policy=p,
    )
    assert missing["status"] == "RISK_INPUT_REQUIRED"
    assert missing["portfolio_allowed"] is False

    ok = evaluate_trade(
        entry=50,
        stop=48.5,
        target=53,
        account_equity=500000,
        daily_pnl=0,
        open_risk=0,
        concurrent_positions=0,
        correlated_open_risk=0,
        drawdown_pct=0,
        consecutive_losses=0,
        grade="A+",
        policy=p,
    )
    assert ok["status"] == "ALLOW"
    assert ok["recommended_shares"] == 2000
    assert ok["net_rr"] == 2.0

    loss_lock = evaluate_trade(
        entry=50,
        stop=48.5,
        target=53,
        account_equity=500000,
        daily_pnl=-10000,
        grade="A+",
        policy=p,
    )
    assert loss_lock["status"] == "BLOCK"

    dd_lock = evaluate_trade(
        entry=50,
        stop=48.5,
        target=53,
        account_equity=500000,
        drawdown_pct=0.06,
        grade="A+",
        policy=p,
    )
    assert dd_lock["state"] == "LOCKDOWN"
    assert dd_lock["status"] == "BLOCK"

    # Research-only cost-after-RR regression: gross 1.5R is not a valid
    # execution-adjusted 1.5R. Never modify a target or widen the stop to pass.
    from src.risk_engine import evaluate_candidate
    from src.cost_profiles import USER_CASH_DAYTRADE_20261022
    paper = {
        "mode": "PAPER_ONLY", "daily_realized_net_pnl_twd": 0,
        "consecutive_stops": 0, "open_positions": 0,
        "open_stop_risk_twd": 0,
    }
    candidate = {"entry": 50.0, "stop": 49.0, "target": 51.5}
    cost = USER_CASH_DAYTRADE_20261022.to_execution_policy(
        entry_slippage_bps=5, exit_slippage_bps=5,
        spread_bps=10, liquidity_penalty_bps=2, enforce_gate=False,
    )
    ctx = {
        "mode": "PAPER_ONLY", "paper_ledger": paper,
        "account_equity": 500000, "daily_pnl": 0, "open_risk": 0,
        "concurrent_positions": 0, "consecutive_losses": 0,
        "execution_policy": cost,
    }
    below = evaluate_candidate(candidate, ctx)
    assert below["gross_rr"] == 1.5
    assert below["status"] == "BLOCK"
    assert below["recommended_shares"] == 0
    assert below["execution_adjusted_rr"] < 1.5
    assert "EXECUTION_RR_BELOW_MINIMUM" in below["reasons"]
    assert candidate == {"entry": 50.0, "stop": 49.0, "target": 51.5}

    # Missing slippage, spread or liquidity inputs must never default to zero.
    ctx["execution_policy"] = USER_CASH_DAYTRADE_20261022.to_execution_policy(
        enforce_gate=False,
    )
    unknown = evaluate_candidate(candidate, ctx)
    assert unknown["status"] == "BLOCK"
    assert unknown["recommended_shares"] == 0
    assert unknown["execution_status"] == "EXECUTION_INPUT_REQUIRED"
    assert candidate["stop"] == 49.0 and candidate["target"] == 51.5

    print("PASS P0-R risk engine tests")


if __name__ == "__main__":
    main()
