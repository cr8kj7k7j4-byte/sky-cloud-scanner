"""W6 offline monitor tests; fixtures do not connect to brokers, GCS or GitHub."""
import unittest
from datetime import datetime, timezone

from scripts.w6_risk_monitor import analyze, fingerprint

NOW = datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc)
SHA = "a" * 40
PR = {"state": "open", "draft": True, "head": {"sha": SHA}}


def run(n, *, status="completed", conclusion="success", sha=SHA, event="pull_request"):
    return {"id": n, "status": status, "conclusion": conclusion,
            "head_sha": sha, "event": event, "created_at": "2026-11-08T04:00:00Z",
            "html_url": f"https://github.com/example/repo/actions/runs/{n}"}


class MonitorTests(unittest.TestCase):
    def test_seventeen_success_is_only_ci(self):
        r = analyze(PR, [run(i) for i in range(1, 18)], NOW)
        self.assertEqual(r["status"], "PR_CI_PASS_ONLY")
        self.assertFalse(r["production_eligible"])
        self.assertFalse(r["broker_ledger_verified"])
        self.assertFalse(r["trading_enabled"])

    def test_failure_alerts_and_is_deterministic(self):
        r = analyze(PR, [run(i) for i in range(1, 17)] + [run(17, conclusion="failure")], NOW)
        self.assertEqual(r["status"], "CI_FAILURE_W0_REVIEW")
        self.assertEqual(r["ci_failure_ids"], [17])
        self.assertEqual(fingerprint(r), fingerprint(r))

    def test_queued_is_not_failure(self):
        r = analyze(PR, [run(i) for i in range(1, 17)]
                    + [run(17, status="queued", conclusion=None)], NOW)
        self.assertEqual(r["status"], "CI_PENDING_OR_INCOMPLETE")

    def test_stale_sha_is_not_counted(self):
        r = analyze(PR, [run(i, sha="b" * 40) for i in range(1, 18)], NOW)
        self.assertEqual(r["ci_success_count"], 0)

    def test_manual_dispatch_is_not_ci(self):
        r = analyze(PR, [run(i, event="workflow_dispatch") for i in range(1, 18)], NOW)
        self.assertEqual(r["ci_success_count"], 0)

    def test_changed_pr_state_is_review(self):
        r = analyze({**PR, "draft": False}, [], NOW)
        self.assertEqual(r["status"], "PR_STATE_CHANGED_REQUIRES_W0_REVIEW")

    def test_missing_sha_fails_closed(self):
        r = analyze({**PR, "head": {}}, [], NOW)
        self.assertEqual(r["status"], "PR_HEAD_UNKNOWN")

    def test_deadline_is_not_permanent_scheduler(self):
        r = analyze(PR, [], datetime(2026, 11, 9, 2, 38, 1, tzinfo=timezone.utc))
        self.assertEqual(r["status"], "MONITOR_WINDOW_ENDED")

    def test_never_auto_repair_or_trade(self):
        r = analyze(PR, [run(1, conclusion="failure")], NOW)
        self.assertFalse(r["safe_automatic_repair_performed"])
        self.assertFalse(r["broker_ledger_verified"])


if __name__ == "__main__":
    unittest.main()
