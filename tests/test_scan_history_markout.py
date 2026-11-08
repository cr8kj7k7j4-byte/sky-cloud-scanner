import unittest
from datetime import datetime, timedelta, timezone
from research.scan_history_markout import research_markout


class ResearchMarkoutTests(unittest.TestCase):
    def test_insufficient_data_is_not_a_prediction(self):
        r = research_markout("1101", "next_day", [])
        self.assertEqual(r["status"], "INSUFFICIENT_DATA")
        self.assertEqual(r["observations"], [])

    def test_fixture_does_not_enable_trading(self):
        start = datetime(2026, 8, 1, tzinfo=timezone(timedelta(hours=8)))
        bars = []
        for i in range(60):
            p = 20 + i * 0.2
            bars.append({"timestamp": (start + timedelta(days=i)).isoformat(),
                         "open": p, "high": p + 0.4, "low": p - 0.4,
                         "close": p + 0.1, "volume": 100 + i})
        r = research_markout("1101", "next_day", bars)
        self.assertFalse(r["production_signal"])
        self.assertEqual(r["schema"], "SKY_RESEARCH_HISTORICAL_MARKOUT_V1")
        for row in r["observations"]:
            self.assertGreater(row["entry_at"], row["signal_at"])
            self.assertTrue(row["research_only"])


if __name__ == "__main__":
    unittest.main()
