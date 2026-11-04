"""Regression tests for the user-confirmed P0-R no-new-entry kill switch."""
import unittest
from src.risk_engine import RiskPolicy, evaluate_trade


class TwoLossHardStopTests(unittest.TestCase):
    def setUp(self):
        self.policy = RiskPolicy(
            risk_per_trade_pct=0.01,
            daily_loss_limit_pct=0.02,
            max_portfolio_heat_pct=0.03,
            max_position_pct=0.20,
            max_concurrent_positions=3,
            caution_loss_streak=3,
            defensive_loss_streak=5,
            lot_size=1,
        )

    def evaluate(self, **changes):
        kwargs = dict(entry=50.0, stop=49.0, target=53.0,
                      account_equity=500000.0, daily_pnl=0.0,
                      open_risk=0.0, concurrent_positions=0,
                      correlated_open_risk=0.0, consecutive_losses=0,
                      grade="A+", policy=self.policy)
        kwargs.update(changes)
        return evaluate_trade(**kwargs)

    def test_two_losses_hard_block_even_when_drawdown_state_is_normal(self):
        result = self.evaluate(consecutive_losses=2)
        self.assertEqual(result["state"], "NORMAL")
        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["portfolio_allowed"])
        self.assertEqual(result["recommended_shares"], 0)
        self.assertIn("連續兩筆虧損，停止新進場", result["reasons"])

    def test_one_loss_does_not_trigger_two_loss_kill_switch(self):
        result = self.evaluate(consecutive_losses=1)
        self.assertNotIn("連續兩筆虧損，停止新進場", result["reasons"])
        self.assertEqual(result["status"], "ALLOW")

    def test_daily_2r_loss_still_hard_blocks(self):
        result = self.evaluate(daily_pnl=-10000.0)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["recommended_shares"], 0)
        self.assertIn("已達 Daily Loss Limit", result["reasons"])


if __name__ == "__main__":
    unittest.main()
