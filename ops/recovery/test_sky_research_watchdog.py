"""Fixture-only tests; never dispatches real GitHub Actions."""
import unittest
from datetime import datetime, timezone, timedelta
from sky_research_watchdog import decide_retry, check_once

NOW = datetime(2026, 11, 9, 2, 0, tzinfo=timezone.utc)
END = NOW + timedelta(hours=12)


def run(**changes):
    r = dict(id=123, run_attempt=1, created_at="2026-11-09T01:00:00Z",
             status="completed", conclusion="failure", event="pull_request")
    r.update(changes)
    return r


class DecisionTests(unittest.TestCase):
    def test_failed_pr_ci_retries(self):
        self.assertEqual(decide_retry(run(), NOW, END)[0], "retry")

    def test_one_retry_allowed(self):
        self.assertEqual(decide_retry(run(run_attempt=2), NOW, END)[0], "retry")

    def test_attempt_cap(self):
        self.assertEqual(decide_retry(run(run_attempt=3), NOW, END)[1], "attempt_limit")

    def test_active_run_no_duplicate(self):
        self.assertEqual(decide_retry(run(status="in_progress"), NOW, END)[1], "already_active")

    def test_success_no_retry(self):
        self.assertEqual(decide_retry(run(conclusion="success"), NOW, END)[0], "skip")

    def test_cancelled_no_retry(self):
        self.assertEqual(decide_retry(run(conclusion="cancelled"), NOW, END)[0], "skip")

    def test_non_pr_no_retry(self):
        self.assertEqual(decide_retry(run(event="schedule"), NOW, END)[1], "not_pr_ci")

    def test_cutoff(self):
        self.assertEqual(decide_retry(run(), END, END)[1], "expired")

    def test_stale_not_retried(self):
        self.assertEqual(decide_retry(run(created_at="2026-11-07T01:00:00Z"), NOW, END)[0], "skip")

    def test_missing_evidence(self):
        r=run();del r["run_attempt"]
        self.assertEqual(decide_retry(r,NOW,END)[1], "missing_run_evidence")

    def test_no_run(self):
        self.assertEqual(decide_retry(None,NOW,END)[1], "no_run")

    def test_dry_run(self):
        invoked = []
        out=check_once(lambda name:[run()], lambda name,id:invoked.append(id),
                       NOW,END,False)
        self.assertEqual(out["items"][0]["action"], "dry_run")
        self.assertEqual(invoked, [])

    def test_bounded_retry_one_workflow(self):
        invoked = []
        out=check_once(lambda name:[run()], lambda name,id:invoked.append((name,id)),
                       NOW,END,True)
        self.assertEqual(out["items"][0]["action"], "retry_requested")
        self.assertEqual(invoked,[("four-strategy-research-contract.yml",123)])

    def test_no_retry_after_deadline(self):
        invoked=[]
        out=check_once(lambda name:[run()], lambda name,id:invoked.append(id),
                       END,END,True)
        self.assertEqual(out["items"][0]["reason"], "expired")
        self.assertFalse(invoked)


if __name__ == "__main__":
    unittest.main()
