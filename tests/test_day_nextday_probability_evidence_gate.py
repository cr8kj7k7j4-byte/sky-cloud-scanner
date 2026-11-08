"""Fail-closed tests: a trend score must never become a probability."""
import unittest
from datetime import datetime, timedelta, timezone
from research.day_nextday_probability_evidence_gate import audit, check_horizon

TPE = timezone(timedelta(hours=8))

class ProbabilityGateTests(unittest.TestCase):
    def test_both_horizons_missing_proof(self):
        result = audit({})
        self.assertEqual(set(result["models"]), {"bidirectional_intraday", "next_day"})
        for row in result["models"].values():
            self.assertEqual(row["status"], "INSUFFICIENT_DATA")
            self.assertFalse(row["display_probability"])
            self.assertFalse(row["production_trade_eligible"])

    def test_untrained_direction_score_not_probability(self):
        result = audit({"models": {"next_day": {"direction": "LONG_WATCH",
                                                  "long_score": 90, "short_score": 10}}})
        self.assertFalse(result["models"]["next_day"]["display_probability"])

    def test_lookahead_and_naive_time_are_rejected(self):
        p = datetime(2026, 11, 6, 9, 5, tzinfo=TPE)
        row = {"prediction_id": "one", "p_up": 0.7, "actual_up": 1,
               "prediction_at": p.isoformat(), "outcome_at": p.isoformat(),
               "symbol": "1101", "regime": "BULL"}
        report = check_horizon([row])
        self.assertIn("timestamp_invalid_or_lookahead", report["errors"])
        row["outcome_at"] = "2026-11-06T13:30:00"
        report = check_horizon([row])
        self.assertIn("timestamp_invalid_or_lookahead", report["errors"])

    def test_duplicate_and_fake_probability_rejected(self):
        p = datetime(2026, 11, 6, 9, 5, tzinfo=TPE)
        row = {"prediction_id": "one", "p_up": 90, "actual_up": 1,
               "prediction_at": p.isoformat(),
               "outcome_at": (p+timedelta(minutes=20)).isoformat(),
               "symbol": "1101", "regime": "BULL"}
        report = check_horizon([row, row])
        self.assertIn("probability_invalid", report["errors"])
        self.assertIn("missing_or_duplicate_prediction_id", report["errors"])

    def test_missing_outcomes_never_count_as_success(self):
        report = check_horizon([{"prediction_id": "a", "p_up": 0.9, "actual_up": None}])
        self.assertEqual(report["observed"]["outcome_coverage"], 0)
        self.assertFalse(report["display_probability"])

    def test_no_production_promotion_even_with_model_claims(self):
        report = check_horizon([], training_verified=True, independent_oos=True,
                               forward_only=True, cost_gate="PASS")
        self.assertFalse(report["display_probability"])
        self.assertFalse(report["production_trade_eligible"])

if __name__ == "__main__":
    unittest.main()
