"""Regression: P0-R two consecutive losses must block new entries, regardless of caution thresholds."""
import unittest
from src.risk_engine import RiskPolicy, evaluate_trade, evaluate_candidate


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

    def test_missing_loss_history_blocks_candidate(self):
        candidate = {"entry": 50, "stop": 49, "target": 54, "grade": "A+"}
        portfolio = {"account_equity": 500000, "daily_pnl": -1000}
        result = evaluate_candidate(candidate, portfolio)
        self.assertEqual(result["status"], "RISK_INPUT_REQUIRED")
        self.assertFalse(result["portfolio_allowed"])
        self.assertEqual(result["recommended_shares"], 0)
        self.assertIn("consecutive_losses", result["required_inputs"])
        portfolio["consecutive_losses"] = None
        self.assertEqual(evaluate_candidate(candidate, portfolio)["status"], "RISK_INPUT_REQUIRED")

    def test_daily_limit_remains_independent(self):
        result = evaluate_trade(
            entry=50, stop=49, target=54, account_equity=500000,
            daily_pnl=-10000, consecutive_losses=0, grade="A+",
            policy=RiskPolicy(risk_per_trade_pct=0.01,
                              daily_loss_limit_pct=0.02, lot_size=1000),
        )
        self.assertEqual(result["status"], "BLOCK")


    def test_each_unknown_account_field_blocks_new_entries(self):
        candidate = {"entry": 50, "stop": 49, "target": 54, "grade": "A+"}
        complete = {"account_equity": 500000, "daily_pnl": 0,
                    "open_risk": 0, "concurrent_positions": 0,
                    "correlated_open_risk": 0, "drawdown_pct": 0,
                    "consecutive_losses": 0}
        for field in ("daily_pnl", "open_risk", "concurrent_positions",
                      "correlated_open_risk", "drawdown_pct", "consecutive_losses"):
            with self.subTest(missing=field):
                missing = dict(complete)
                missing.pop(field)
                result = evaluate_candidate(candidate, missing)
                self.assertEqual(result["status"], "RISK_INPUT_REQUIRED")
                self.assertEqual(result["state"], "UNKNOWN")
                self.assertFalse(result["portfolio_allowed"])
                self.assertEqual(result["recommended_shares"], 0)
                self.assertIn(field, result["required_inputs"])

    def test_complete_explicit_account_zero_inputs_are_not_missing(self):
        candidate = {"entry": 50, "stop": 49, "target": 54, "grade": "A+"}
        complete = {"account_equity": 500000, "daily_pnl": 0,
                    "open_risk": 0, "concurrent_positions": 0,
                    "correlated_open_risk": 0, "drawdown_pct": 0,
                    "consecutive_losses": 0}
        result = evaluate_candidate(candidate, complete)
        self.assertNotEqual(result["status"], "RISK_INPUT_REQUIRED")
        self.assertEqual(result["required_inputs"], [])


if __name__ == "__main__":
    unittest.main()
