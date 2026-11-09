"""Regression: Fugle-only mode must never query free MIS market quotes."""
import os
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.quote_provider import collect_market_quotes


class TestFugleOnlyMarketData(unittest.TestCase):
    def test_blocked_fugle_does_not_fall_back_to_mis(self):
        calls = []
        def fugle(universe, trading_date=None):
            calls.append("fugle")
            return [], ["FUGLE_DIAGNOSTIC"]
        def forbidden_mis(universe):
            raise AssertionError("MIS must not be requested")
        with patch.dict(os.environ, {"SKY_FUGLE_ONLY_MARKETDATA": "1"}):
            result = collect_market_quotes(
                [], now=datetime(2026, 11, 9, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")),
                fugle_fetch=fugle, mis_fetch=forbidden_mis,
            )
        self.assertEqual(calls, ["fugle"])
        self.assertFalse(result["fallback_used"])
        self.assertIn("FUGLE_ONLY_NO_FREE_MARKETDATA_FALLBACK", result["warnings"])
        self.assertEqual(result["provider"], "Fugle bulk snapshot (partial research)")
        self.assertEqual(result["rows"], [])


if __name__ == "__main__":
    unittest.main()
