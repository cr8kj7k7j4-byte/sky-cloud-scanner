import unittest
from ops.recovery.sky_intraday_readiness import classify


class TestReadiness(unittest.TestCase):
    def test_no_live_evidence_remains_blocked(self):
        x = classify({"id": 1, "status": "completed", "conclusion": "success"},
                     {"all_market_universe_count": 1983,
                      "all_market_observed_price_count": 1940,
                      "all_market_fresh_executed_count": 0,
                      "trade_eligible": False})
        self.assertEqual(x["readiness"], "BLOCKED")
        self.assertEqual(x["snapshot_observed"], 1940)

    def test_failed_run_remains_blocked(self):
        x = classify({"status": "completed", "conclusion": "failure"},
                     {"all_market_universe_count": 5,
                      "all_market_fresh_executed_count": 5,
                      "trade_eligible": True})
        self.assertEqual(x["readiness"], "BLOCKED")

    def test_missing_run_remains_blocked(self):
        self.assertEqual(classify(None, {})["readiness"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
