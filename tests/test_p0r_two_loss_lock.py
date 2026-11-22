"""Regression: P0-R two consecutive losses must block new entries, regardless of caution thresholds."""
import unittest
from src.risk_engine import RiskPolicy, evaluate_trade


class TwoLossEntryLockTests(unittest.TestCase):
    def test_two_losses_block_even_with_default_three_loss_caution(self):
        for losses in (2, 3, 5):
            with self.subTest(losses=losses):
                result = evaluate_trade(
                    entry=50, stop=49, target=54, account_equity=500000,
                    daily_pnl=-2000, consecutive_losses=losses, grade="A+",
                    policy=RiskPolicy(risk_per_trade_pct=0.01,
                                      daily_loss_limit_pct=0.02, lot_size=1000),
                )
                self.assertEqual(result["status"], "BLOCK")
                self.assertFalse(result["portfolio_allowed"])
                self.assertEqual(result["recommended_shares"], 0)
                self.assertTrue(any("連續兩筆停損" in r for r in result["reasons"]))

    def test_one_loss_not_locked_by_streak_alone(self):
        result = evaluate_trade(
            entry=50, stop=49, target=54, account_equity=500000,
            daily_pnl=-1000, consecutive_losses=1, grade="A+",
            policy=RiskPolicy(risk_per_trade_pct=0.01,
                              daily_loss_limit_pct=0.02, lot_size=1000),
        )
        self.assertEqual(result["status"], "ALLOW")

    def test_daily_limit_remains_independent(self):
        result = evaluate_trade(
            entry=50, stop=49, target=54, account_equity=500000,
            daily_pnl=-10000, consecutive_losses=0, grade="A+",
            policy=RiskPolicy(risk_per_trade_pct=0.01,
                              daily_loss_limit_pct=0.02, lot_size=1000),
        )
        self.assertEqual(result["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
