"""Pure offline tests for bounded read-only overnight acceptance checks."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sky_overnight_readonly_acceptance import observe


class OvernightReadOnlyTests(unittest.TestCase):
    def test_outside_window_never_fetches(self):
        result = observe(datetime(2026, 11, 10, 1, 31, tzinfo=timezone.utc),
                         lambda _: self.fail("unexpected API call"))
        self.assertEqual(result["status"], "OUTSIDE_MONITOR_WINDOW")
        self.assertFalse(result["monitoring_active"])

    def test_failed_scanner_reported_not_retried(self):
        seen = []
        def fetch(name):
            seen.append(name)
            return [{"id": 123, "event": "schedule", "status": "completed",
                     "conclusion": "failure" if name == "scan.yml" else "success"}]
        result = observe(datetime(2026, 11, 9, 14, 0, tzinfo=timezone.utc), fetch)
        self.assertEqual(result["status"], "WORKFLOW_FAILURES_DETECTED")
        self.assertEqual(result["checks"]["intraday_scan"]["finding"], "WORKFLOW_FAILURE")
        self.assertFalse(result["production_trading_approved"])
        self.assertEqual(len(seen), 5)

    def test_success_does_not_imply_trading_or_mobile(self):
        result = observe(datetime(2026, 11, 9, 14, 0, tzinfo=timezone.utc),
                         lambda _: [{"id": 10, "status": "completed", "conclusion": "success"}])
        self.assertEqual(result["status"], "WORKFLOWS_FINISHED_NOT_END_TO_END_VERIFIED")
        self.assertFalse(result["mobile_end_to_end_verified"])


if __name__ == "__main__":
    unittest.main()
