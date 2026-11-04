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
    assert ok["recommended_shares"] == 1000
    assert ok["net_rr"] == 2.0

    loss_lock = evaluate_trade(
        entry=50,
        stop=48.5,
        target=53,
        account_equity=500000,
        daily_pnl=-7500,
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

    # This workflow runs the module as a script, not via pytest discovery.
    # Explicitly invoke the added hard-stop regression checks.
    test_two_consecutive_losses_hard_block_even_a_plus()
    test_daily_loss_two_r_hard_block()
    print("PASS P0-R risk engine tests")


if __name__ == "__main__":
    main()


def test_two_consecutive_losses_hard_block_even_a_plus():
    p = RiskPolicy(risk_per_trade_pct=0.01, daily_loss_limit_pct=0.02, lot_size=1000)
    base = dict(entry=50, stop=48.5, target=54, account_equity=500000,
                daily_pnl=0, open_risk=0, concurrent_positions=0,
                correlated_open_risk=0, grade="A+", policy=p)
    one = evaluate_trade(consecutive_losses=1, **base)
    two = evaluate_trade(consecutive_losses=2, **base)
    assert one["status"] == "ALLOW"
    assert two["status"] == "BLOCK"
    assert two["portfolio_allowed"] is False
    assert two["recommended_shares"] == 0
    assert any("連續兩筆" in reason for reason in two["reasons"])


def test_daily_loss_two_r_hard_block():
    p = RiskPolicy(risk_per_trade_pct=0.01, daily_loss_limit_pct=0.02, lot_size=1000)
    result = evaluate_trade(entry=50, stop=48.5, target=54,
                            account_equity=500000, daily_pnl=-10000,
                            consecutive_losses=0, grade="A+", policy=p)
    assert result["status"] == "BLOCK"
    assert result["recommended_shares"] == 0
