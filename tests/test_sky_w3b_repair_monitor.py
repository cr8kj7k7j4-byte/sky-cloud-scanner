import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from research.sky_w3b_repair_monitor import decide, monitor

NOW = datetime(2026, 11, 10, 13, 0, tzinfo=timezone.utc)
SHA = "a" * 40


def pr(state="open", merged=False, sha=SHA):
    return {"state": state, "merged": merged, "draft": True, "head": {"sha": sha}}


def run(status="completed", conclusion="success", attempt=1, sha=SHA,
        event="pull_request", workflow="sky-chat-bridge-tests.yml",
        age_minutes=5):
    return {"id": 12345, "status": status, "conclusion": conclusion,
            "run_attempt": attempt, "head_sha": sha, "event": event,
            "path": ".github/workflows/" + workflow,
            "created_at": (NOW - timedelta(minutes=age_minutes)).isoformat(),
            "html_url": "https://github.com/example/repo/actions/runs/12345"}


class W3BRepairMonitorTests(unittest.TestCase):
    def test_passing_unit_ci_never_promotes(self):
        result = decide(pr(), [run()], NOW)
        self.assertEqual(result["action"], "review_required")
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["vwap_certified"])
        self.assertFalse(result["real_market_5m_certified"])

    def test_one_fresh_failed_unit_ci_may_retry(self):
        result = decide(pr(), [run(conclusion="failure")], NOW)
        self.assertEqual(result["action"], "retry_candidate")

    def test_retries_are_bounded(self):
        self.assertEqual(decide(pr(), [run(conclusion="failure", attempt=2)], NOW)["action"], "blocked")
        self.assertEqual(decide(pr(), [run(conclusion="failure", age_minutes=120)], NOW)["action"], "blocked")

    def test_wrong_sha_event_and_workflow_never_retry(self):
        for bad in (run(conclusion="failure", sha="b"*40),
                    run(conclusion="failure", event="schedule"),
                    run(conclusion="failure", workflow="scan.yml")):
            self.assertEqual(decide(pr(), [bad], NOW)["action"], "blocked")

    def test_running_and_unknown_are_not_retried(self):
        self.assertEqual(decide(pr(), [run(status="in_progress")], NOW)["action"], "observe")
        self.assertEqual(decide(pr(), [], NOW)["reason"], "NO_CURRENT_HEAD_UNIT_CI")

    def test_pr_closed_or_merged_must_not_retry(self):
        self.assertEqual(decide(pr(state="closed"), [run(conclusion="failure")], NOW)["action"], "blocked")
        result = decide(pr(state="closed", merged=True), [run()], NOW)
        self.assertEqual(result["action"], "review_required")
        self.assertFalse(result["w0_p0g_approved"])


    def test_closed_unmerged_monitor_records_blocker_without_failing_watchdog(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "w3b_repair_monitor.json"
            def fake_api(method, url, token):
                if "/pulls/512" in url:
                    return pr(state="closed")
                if "/actions/runs?" in url:
                    return {"workflow_runs": [run(conclusion="failure")]}
                self.fail("Unexpected request: " + method + " " + url)
            with patch("research.sky_w3b_repair_monitor.api", side_effect=fake_api), \
                 patch("research.sky_w3b_repair_monitor.OUTPUT", path), \
                 patch.dict(os.environ, {"GH_TOKEN":"test", "GITHUB_REPOSITORY":"example/repo", "SKY_W3B_SAFE_CI_RETRY":"true"}):
                monitor()
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(report["reason"], "PR_CLOSED_UNMERGED")
            self.assertEqual(report["action"], "blocked")
            self.assertFalse(report["production_eligible"])
            self.assertFalse(report["real_market_5m_certified"])


if __name__ == "__main__":
    unittest.main()
