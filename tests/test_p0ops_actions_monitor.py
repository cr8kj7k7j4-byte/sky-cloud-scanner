"""P0-OPS monitor tests using deterministic timestamps; no external API calls."""
import unittest
from research.p0ops_actions_monitor import assess, seconds_between, summarize_run


class MonitorTests(unittest.TestCase):
    def test_queue_uses_actual_job_start_not_run_started(self):
        run = {"id": 42, "status": "completed", "conclusion": "failure",
               "created_at": "2026-11-04T01:51:44Z",
               "run_started_at": "2026-11-04T01:51:44Z"}
        job = {"started_at": "2026-11-04T02:09:34Z",
               "completed_at": "2026-11-04T02:12:09Z",
               "steps": [{"name": "Verify operational market coverage", "conclusion": "failure"}]}
        row = summarize_run(run, job)
        self.assertEqual(row["queue_seconds"], 1070)
        self.assertEqual(row["job_seconds"], 155)
        self.assertEqual(row["failed_steps"], ["Verify operational market coverage"])
        self.assertIn("RUNNER_QUEUE_OVER_5M", assess("scan.yml", [row]))

    def test_consecutive_scan_failure_and_missing_data(self):
        bad = {"conclusion": "failure", "queue_seconds": None, "job_seconds": None}
        self.assertEqual(assess("scan.yml", [bad, bad]),
                         ["LATEST_RUN_FAILED", "CONSECUTIVE_SCAN_FAILURES"])
        self.assertEqual(assess("scan.yml", []), ["NO_COMPLETED_RUN_FOUND"])

    def test_swing_failure_and_dashboard_success(self):
        failed = {"conclusion": "failure", "queue_seconds": 12, "job_seconds": 650}
        good = {"conclusion": "success", "queue_seconds": 12, "job_seconds": 30}
        self.assertEqual(assess("swing-live-scan.yml", [failed]),
                         ["LATEST_RUN_FAILED", "JOB_RUNTIME_OVER_10M"])
        self.assertEqual(assess("shadow-promotion-dashboard.yml", [good]), [])

    def test_missing_timestamps_do_not_invent_seconds(self):
        self.assertIsNone(seconds_between(None, "2026-11-04T02:00:00Z"))


if __name__ == "__main__":
    unittest.main()
