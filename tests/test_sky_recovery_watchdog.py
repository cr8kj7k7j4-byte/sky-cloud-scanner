import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo
from research.sky_recovery_watchdog import COLUMNS, check_contract, collect

class RecoveryWatchdogTests(unittest.TestCase):
    def test_13_column_contract(self):
        self.assertEqual(len(COLUMNS), 13)
        self.assertEqual(check_contract(), [])

    @patch("research.sky_recovery_watchdog.read_json")
    def test_unverified_market_never_pretends_tradable(self, read_json):
        read_json.side_effect = [
            {
                "all_market_universe_count": 1983,
                "all_market_observed_price_count": 1940,
                "all_market_fresh_executed_count": 0,
                "published_at_utc": "2026-11-09T05:53:49+00:00",
                "run_id": "123",
            },
            {"run_id": "124", "decision": "DATA_COVERAGE_INSUFFICIENT_NO_TRADE"},
        ]
        now = datetime(2026, 11, 9, 13, 58, tzinfo=ZoneInfo("Asia/Taipei"))
        report = collect(now)
        self.assertEqual(report["code_contract"], "PASS")
        self.assertEqual(report["observed_price_count"], 1940)
        self.assertEqual(report["market_status"], "DATA_BLOCKED_UNVERIFIED_EXECUTION")
        self.assertFalse(report["production_trade_eligible"])
        self.assertEqual(report["mobile_api_e2e"], "NOT_VERIFIED")

    @patch("research.sky_recovery_watchdog.read_json", return_value=None)
    def test_missing_report_is_not_certified(self, _):
        now = datetime(2026, 11, 10, 9, 5, tzinfo=ZoneInfo("Asia/Taipei"))
        report = collect(now)
        self.assertEqual(report["market_status"], "STALE_OR_MISSING_REPORT")
        self.assertFalse(report["production_trade_eligible"])

if __name__ == "__main__":
    unittest.main()
