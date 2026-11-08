"""Offline W2 watchdog contracts; no network, paid API or cloud access."""
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from research.w2_research_24h_watchdog import START, END, WORKFLOWS, assess


def run(minute, *, state="completed", conclusion="success",
        event="workflow_dispatch", branch="main", ident=123):
    return {"id": ident, "created_at": (START + timedelta(minutes=minute)).isoformat(),
            "status": state, "conclusion": conclusion, "event": event,
            "head_branch": branch, "html_url": "https://github.com/example/actions/runs/123"}


class WatchdogTest(unittest.TestCase):
    def test_success_and_no_runs_are_not_false_schedule_proofs(self):
        now = START + timedelta(hours=4)
        self.assertEqual(assess(now, {})["status"], "NO_CONFIRMED_FAILURE")
        result = assess(now, {WORKFLOWS[0]: [run(10)]})
        self.assertEqual(result["observed_runs"], 1)
        self.assertFalse(result["schedule_identity_verified"])
        self.assertFalse(result["gcs_readback_verified"])

    def test_research_failure_detected(self):
        result = assess(START + timedelta(hours=3),
                        {WORKFLOWS[1]: [run(10, conclusion="failure")]})
        self.assertEqual(result["status"], "ATTENTION")
        self.assertEqual(result["failures"][0]["reason"], "COMPLETED_NOT_SUCCESSFUL")

    def test_pr_and_unrelated_branches_not_alerted(self):
        result = assess(START + timedelta(hours=3),
                        {WORKFLOWS[0]: [run(10, conclusion="failure", event="pull_request"),
                                         run(11, conclusion="failure", branch="dev")]})
        self.assertEqual(result["status"], "NO_CONFIRMED_FAILURE")

    def test_pending_over_45_minutes_alerts_but_recent_does_not(self):
        now = START + timedelta(minutes=100)
        result = assess(now, {WORKFLOWS[1]: [run(53, state="in_progress", conclusion=None),
                                              run(60, state="queued", conclusion=None)]})
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["failures"][0]["reason"], "RUN_STALLED_OVER_45_MIN")

    def test_old_known_failure_not_realerted(self):
        result = assess(START + timedelta(hours=1),
                        {WORKFLOWS[2]: [run(-30, conclusion="failure")]})
        self.assertEqual(result["status"], "NO_CONFIRMED_FAILURE")

    def test_future_or_expired_observation_ignored(self):
        result = assess(START + timedelta(hours=1),
                        {WORKFLOWS[0]: [run(200, conclusion="failure"),
                                         run(int((END - START).total_seconds() / 60),
                                             conclusion="failure")]})
        self.assertEqual(result["observed_runs"], 0)

    def test_dedup_scans_second_page_without_posting(self):
        from research import w2_research_24h_watchdog as wd
        failure = {"workflow": wd.WORKFLOWS[0], "run_id": 42, "reason": "COMPLETED_NOT_SUCCESSFUL",
                   "event": "schedule", "conclusion": "failure"}
        key = "W2_WATCHDOG_EVENT:" + failure["workflow"] + ":42:COMPLETED_NOT_SUCCESSFUL"
        pages = [[{"body": "unrelated"}] * 100, [{"body": key}]]
        calls = []

        def fake_api(method, path, body=None):
            calls.append((method, path))
            if method == "GET":
                return pages[int(path.rsplit("=", 1)[1]) - 1]
            raise AssertionError("duplicate alert must not be posted")

        with patch.object(wd, "_api", side_effect=fake_api):
            self.assertEqual(wd.alert_once(failure), "ALREADY_RECORDED")
        self.assertEqual(len(calls), 2)

    def test_new_failure_posts_after_last_page(self):
        from research import w2_research_24h_watchdog as wd
        failure = {"workflow": wd.WORKFLOWS[0], "run_id": 43, "reason": "COMPLETED_NOT_SUCCESSFUL",
                   "event": "schedule", "conclusion": "failure", "url": "https://example.invalid/43"}
        calls = []

        def fake_api(method, path, body=None):
            calls.append((method, path, body))
            return [] if method == "GET" else {}

        with patch.object(wd, "_api", side_effect=fake_api):
            self.assertEqual(wd.alert_once(failure), "ISSUE_COMMENT_CREATED")
        self.assertEqual([x[0] for x in calls], ["GET", "POST"])
        self.assertIn("W2_WATCHDOG_EVENT:", calls[-1][2]["body"])

    def test_pagination_limit_fails_closed_without_duplicate_post(self):
        from research import w2_research_24h_watchdog as wd
        failure = {"workflow": wd.WORKFLOWS[0], "run_id": 44, "reason": "COMPLETED_NOT_SUCCESSFUL"}
        with patch.object(wd, "_api", return_value=[{"body": "x"}] * 100) as api:
            with self.assertRaisesRegex(RuntimeError, "pagination_limit"):
                wd.alert_once(failure)
        self.assertEqual(api.call_count, 20)

    def test_malformed_comment_page_fails_closed(self):
        from research import w2_research_24h_watchdog as wd
        failure = {"workflow": wd.WORKFLOWS[0], "run_id": 45, "reason": "COMPLETED_NOT_SUCCESSFUL"}
        with patch.object(wd, "_api", return_value={"message": "bad"}) as api:
            with self.assertRaisesRegex(RuntimeError, "invalid_response"):
                wd.alert_once(failure)
        api.assert_called_once()


if __name__ == "__main__":
    unittest.main()
