import unittest
from src.scan_history_replay import replay_day


class ScanHistoryReplayTests(unittest.TestCase):
    def test_all_five_minute_slots_without_fabricated_trades(self):
        report = replay_day("2026-11-06")
        self.assertEqual(report["slots"], 53)
        self.assertTrue(report["all_unique"])
        self.assertEqual(report["first"], "2026-11-06T09:05:00+08:00")
        self.assertEqual(report["last"], "2026-11-06T13:25:00+08:00")
        self.assertFalse(report["live_market_verified"])
        self.assertFalse(report["gcs_write_verified"])

    def test_weekend_rejected(self):
        with self.assertRaises(ValueError):
            replay_day("2026-11-08")


if __name__ == "__main__":
    unittest.main()
