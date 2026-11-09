import unittest
from research.sky_observation_only import build_report

class ObservationReportTests(unittest.TestCase):
    def test_blocked_still_exposes_existing_observation(self):
        r = build_report({"run_time": "2026-11-09T11:00:00+08:00",
            "market_data_gate": "BLOCKED_EXTERNAL_DATA_NO_TRADE",
            "quote_coverage_pct": 2.77, "deep_unverified":
            [{"symbol":"1101","name":"台泥","price":27.05}]})
        self.assertEqual(r["observations"][0]["symbol"], "1101")
        self.assertFalse(r["trade_eligible"])
        self.assertFalse(r["full_market_prediction_verified"])
    def test_no_data_never_invents_stocks_or_probabilities(self):
        r = build_report({"market_data_gate": "BLOCKED_EXTERNAL_DATA_NO_TRADE"})
        self.assertEqual(r["observations"], [])
        self.assertIsNotNone(r["no_observation_reason"])
        self.assertNotIn("up_probability", r)
    def test_passing_data_still_not_ai_certification(self):
        r = build_report({"market_data_gate":"PASS_FULL_MARKET_LIVE",
            "operational_full_market_scan":True,"full_market_scan":True})
        self.assertTrue(r["market_data_verified"])
        self.assertFalse(r["full_market_prediction_verified"])
        self.assertFalse(r["trade_eligible"])

if __name__ == "__main__":
    unittest.main()
