"""Regression tests for P0-R hard stops: additive, no automatic trading."""
import unittest

from src.risk_engine import evaluate_trade, RiskPolicy


class TestTwoLossKillSwitch(unittest.TestCase):
    def base(self, **changes):
        args = dict(
            entry=50.0,
            stop=49.0,
            target=53.0,
            account_equity=500000,
            daily_pnl=0,
            open_risk=0,
            concurrent_positions=0,
            correlated_open_risk=0,
            consecutive_losses=0,
            policy=RiskPolicy(risk_per_trade_pct=.01, daily_loss_limit_pct=.02, max_portfolio_heat_pct=.03),
        )
        args.update(changes)
        return evaluate_trade(**args)

    def test_second_consecutive_stop_loss_blocks_new_trade(self):
        result = self.base(consecutive_losses=2, grade="A+")
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["recommended_shares"], 0)
        self.assertTrue(any("連續兩筆停損" in x for x in result["reasons"]))

    def test_daily_two_r_loss_blocks(self):
        result = self.base(daily_pnl=-10000)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["recommended_shares"], 0)

    def test_long_stop_above_entry_is_blocked(self):
        result = self.base(stop=51.0)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["recommended_shares"], 0)

    def test_one_loss_does_not_alone_trigger_hard_stop(self):
        result = self.base(consecutive_losses=1)
        self.assertFalse(any("連續兩筆停損" in x for x in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
