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
