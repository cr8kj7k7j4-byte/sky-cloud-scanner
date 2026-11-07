import unittest
from research.fugle_0050_fixed_trend_replay import simulate, run


class FugleFixedReplayTests(unittest.TestCase):
    def test_no_api_key_fail_closed(self):
        x = run("")
        self.assertEqual(x["status"], "INSUFFICIENT_DATA")
        self.assertFalse(x["production_signal"])

    def test_uses_prior_session_signal_not_future_session(self):
        # Short synthetic sequence: no warmup -> trend never enters.
        series = [("2026-01-%02d" % i, 10., 10. + 0.1 * i) for i in range(1, 11)]
        x = simulate(series, .0045, "TREND")
        self.assertEqual(x["entry_count"], 0)
        self.assertEqual(x["n_sessions"], 10)

    def test_buyhold_starts_on_first_research_session(self):
        series = [("2025-11-09", 10., 10.), ("2025-11-10", 10., 10.),
                  ("2025-11-11", 10., 11.)]
        x = simulate(series, .0045, "BUY_HOLD")
        self.assertEqual(x["entry_count"], 1)
        self.assertEqual(x["n_sessions"], 2)
        self.assertTrue(x["final_position_unrealized"])


if __name__ == "__main__":
    unittest.main()
