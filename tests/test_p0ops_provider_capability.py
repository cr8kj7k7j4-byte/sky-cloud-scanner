"""Deterministic permission preflight tests; no external network."""
import unittest
from research.p0ops_provider_capability import classify_exception, readiness


class CapabilityTests(unittest.TestCase):
    def test_no_secret_leak_and_plan_block(self):
        self.assertEqual(classify_exception(PermissionError("secret TEST_API_KEY=foo")), "PLAN_BLOCKED")

    def test_all_bulk_sources_required(self):
        self.assertEqual(readiness({"fugle_bulk_TSE": "AVAILABLE", "fugle_bulk_OTC": "PLAN_BLOCKED"})["status"],
                         "BLOCKED_BULK_MARKET_PERMISSION")
        good = readiness({"fugle_bulk_TSE": "AVAILABLE", "fugle_bulk_OTC": "AVAILABLE"})
        self.assertEqual(good["status"], "PERMISSION_READY_NEEDS_LIVE_COVERAGE")
        self.assertFalse(good["market_wide_executed_trade_certified"])
        self.assertFalse(good["official_tpex_live_certified"])

    def test_missing_key_and_rate_limit(self):
        self.assertEqual(classify_exception(RuntimeError("Missing FUGLE_API_KEY")), "NO_API_KEY")
        class Error(Exception):
            response = type("Response", (), {"status_code": 429})()
        self.assertEqual(classify_exception(Error()), "RATE_LIMITED")


if __name__ == "__main__":
    unittest.main()
