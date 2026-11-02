import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from src.quote_freshness import validate_quote_timestamp, validate_coverage

NOW = datetime(2026, 11, 2, 11, 42, tzinfo=ZoneInfo("Asia/Taipei"))


class QuoteFreshnessTests(unittest.TestCase):
    def test_valid_quote(self):
        self.assertTrue(validate_quote_timestamp(quote_time="11:41:00", trade_date="2026-11-02", now=NOW)["ok"])

    def test_stale_date_not_inferred(self):
        self.assertEqual(validate_quote_timestamp(quote_time="10:58:00", trade_date="2026-11-02", now=NOW)["status"], "STALE_QUOTE")

    def test_missing_date_rejected(self):
        self.assertEqual(validate_quote_timestamp(quote_time="11:41:00", now=NOW)["status"], "MISSING_TRADE_DATE")

    def test_future_timestamp_rejected(self):
        self.assertEqual(validate_quote_timestamp(quote_time="11:45:00", trade_date="2026-11-02", now=NOW)["status"], "FUTURE_QUOTE_TIMESTAMP")

    def test_naive_iso_rejected(self):
        self.assertEqual(validate_quote_timestamp(quote_time="2026-11-02T11:41:00", now=NOW)["status"], "AMBIGUOUS_TIMEZONE")

    def test_utc_iso(self):
        self.assertTrue(validate_quote_timestamp(quote_time="2026-11-02T03:41:00Z", now=NOW)["ok"])

    def test_sparse_actual_scan(self):
        v = validate_coverage(valid_quotes=100, universe_count=1985)
        self.assertFalse(v["ok"])
        self.assertEqual(v["coverage_pct"], 5.04)

    def test_good_coverage(self):
        self.assertTrue(validate_coverage(valid_quotes=1500, universe_count=1985)["ok"])


if __name__ == "__main__":
    unittest.main()
