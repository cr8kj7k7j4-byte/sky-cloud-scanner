"""Offline W2 watchdog contracts; no network, paid API or cloud access."""
import unittest
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


if __name__ == "__main__":
    unittest.main()
