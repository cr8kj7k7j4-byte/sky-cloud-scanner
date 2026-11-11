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


class PaidRequestSafetyBridgeTests(unittest.TestCase):
    """No-paid-provider regression visible to the canonical main watchdog PR gate."""

    def test_workflow_mock_receipt_distinguishes_pr_head_from_checkout(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-recovery-watchdog.yml").read_text(encoding="utf-8")
        self.assertIn("SKY_PR_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}", workflow)
        self.assertIn("'pull_request_head_sha':os.getenv('SKY_PR_HEAD_SHA')", workflow)
        self.assertIn("'workflow_checkout_sha':os.getenv('GITHUB_SHA')", workflow)
        self.assertIn("PR_MERGE_CHECKOUT_NOT_HEAD", workflow)

    def test_atomic_contract_requires_real_shared_store_not_bool_flag(self):
        from research.sky_paid_api_dedup_contract import (
            canonical_request_key, reserve, finalize_ready,
        )
        from tests.test_sky_paid_api_dedup_contract import SharedMockStore
        key = canonical_request_key("FUGLE", "/snapshot", {"market":"TWSE"},
                                    "authorized-plan", "2026-11-11")
        store = SharedMockStore()
        self.assertEqual(reserve(store, key, "runner-1", "attempt-1"), "CALL_ONCE")
        self.assertEqual(reserve(store, key, "runner-2", "attempt-1"), "BLOCK_IN_FLIGHT")
        self.assertFalse(finalize_ready(store, key, "runner-1", "attempt-1",
                                        "gs://results/verified", "z"*64))
        self.assertEqual(reserve(store, key, "runner-2", "attempt-2"), "BLOCK_IN_FLIGHT")
        # A successful mock test is NOT a distributed real-runner shared lock.

if __name__ == "__main__":
    unittest.main()
