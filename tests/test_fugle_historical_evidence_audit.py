import unittest
from research.fugle_historical_evidence_audit import audit, clean_rows, cross_check


class TestFugleHistoricalAudit(unittest.TestCase):
    def test_missing_key_fail_closed(self):
        result = audit("", "")
        self.assertFalse(result["fugle_key_present"])
        self.assertFalse(result["production_signal"])
        self.assertFalse(result["event_pit_verified"])
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")

    def test_reject_invalid_ohlc(self):
        rows, q = clean_rows({"data": [
            {"date": "2026-11-06", "open": 52, "high": 50, "low": 49,
             "close": 51, "volume": 1000},
        ]})
        self.assertEqual(len(rows), 0)
        self.assertEqual(q["invalid_rows"], 1)
        self.assertFalse(q["schema_ok"])

    def test_detect_duplicate_date(self):
        a = {"date": "2026-11-06", "open": 49, "high": 50, "low": 48,
             "close": 49.5, "volume": 1000}
        rows, q = clean_rows({"data": [a, dict(a)]})
        self.assertEqual(len(rows), 1)
        self.assertEqual(q["duplicate_or_repeated_dates"], 1)

    def test_intraday_requires_timezone(self):
        rows, q = clean_rows({"data": [
            {"date": "2026-11-06T09:00:00", "open": 49, "high": 50,
             "low": 48, "close": 49.5, "volume": 10},
        ]}, intraday=True)
        self.assertFalse(rows)
        self.assertEqual(q["invalid_rows"], 1)

    def test_cross_source_raw_price_match(self):
        raw = {"2026-11-06": {"close": 48.5}}
        result = cross_check(raw, {"2026-11-06": 48.5})
        self.assertEqual(result["common_sessions"], 1)
        self.assertTrue(result["same_date_close_match"])

    def test_cross_source_detects_mismatch(self):
        raw = {"2026-11-06": {"close": 48.5}}
        result = cross_check(raw, {"2026-11-06": 49.5})
        self.assertEqual(result["mismatch_sessions_above_0_02pct"], 1)
        self.assertFalse(result["same_date_close_match"])


if __name__ == "__main__":
    unittest.main()
