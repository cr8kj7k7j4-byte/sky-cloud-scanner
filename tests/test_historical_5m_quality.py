import unittest
from research.historical_5m_quality import inspect_history


def bar(stamp="2026-11-06T09:00:00+08:00", **overrides):
    item={"date":stamp,"open":10,"high":12,"low":9,"close":11,"volume":100}
    item.update(overrides)
    return item


class QualityTest(unittest.TestCase):
    def test_valid_bars_are_observations_not_completeness(self):
        x=inspect_history([bar(),bar("2026-11-06T09:05:00+08:00")])
        self.assertEqual(x["status"],"DATA_OBSERVED")
        self.assertEqual(x["distinct_session_dates"],1)
        self.assertFalse(x["full_period_complete"])
        self.assertEqual(x["sessions_below_observed_max_bars"], 0)
        self.assertNotIn("weekday_sessions_below_55_bars", x)

    def test_duplicates_and_bad_prices_fail(self):
        x=inspect_history([bar(),bar(close=20)])
        self.assertEqual(x["status"],"INVALID_DATA")
        self.assertEqual(x["invalid_counts"]["duplicate_timestamp"],1)
        self.assertEqual(x["invalid_counts"]["invalid_ohlcv_relationship"],1)

    def test_weekend_and_timezone(self):
        x=inspect_history([bar("2026-11-07T09:00:00+08:00"),bar("2026-11-06T09:05:00")])
        self.assertEqual(x["status"],"INVALID_DATA")
        self.assertEqual(x["invalid_counts"]["weekend_candle"],1)
        self.assertEqual(x["invalid_counts"]["missing_timezone"],1)

    def test_outside_session_and_range(self):
        x=inspect_history([bar("2026-10-01T08:55:00+08:00"),
                           bar("2025-12-31T09:00:00+08:00")])
        self.assertEqual(x["invalid_counts"]["outside_regular_session"],1)
        self.assertEqual(x["invalid_counts"]["outside_requested_range"],1)


if __name__ == "__main__":
    unittest.main()
