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

    # Two consecutive losses must hard-block new positions even when
    # the legacy 3-loss caution state is still NORMAL.
    two_loss_stop = evaluate_trade(
        entry=50, stop=48.5, target=53,
        account_equity=500000, consecutive_losses=2,
        grade="A+", policy=p,
    )
    assert two_loss_stop["state"] == "NORMAL"
    assert two_loss_stop["status"] == "BLOCK"
    assert two_loss_stop["portfolio_allowed"] is False
    assert two_loss_stop["recommended_shares"] == 0
    assert "連續兩筆虧損，停止新進場" in two_loss_stop["reasons"]

    single_loss = evaluate_trade(
        entry=50, stop=48.5, target=53,
        account_equity=500000, consecutive_losses=1,
        grade="A+", policy=p,
    )
    assert single_loss["status"] == "ALLOW"

    print("PASS P0-R risk engine tests")


if __name__ == "__main__":
    main()
