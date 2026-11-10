import unittest
from datetime import datetime, timezone
from research.sky_p0r_repair_status import evaluate, safe_retry_candidate, schedule_cadence


class P0RRepairMonitorTests(unittest.TestCase):
    def fixtures(self):
        pr = {"state": "open", "draft": True, "merged": False,
              "html_url": "https://github.com/example/repo/pull/508",
              "head": {"sha": "abc"}, "updated_at": "2026-11-10T12:00:00Z"}
        checks = {"check_runs": [{"status": "completed", "conclusion": "success"}]}
        paper = {"workflow_runs": [{"head_sha": "abc", "id": 42, "status": "completed",
                                   "conclusion": "success", "html_url": "https://example.test/run"}]}
        artifacts = {"artifacts": [{"name": "sky-paper-only-acceptance-42", "expired": False}]}
        return pr, checks, paper, artifacts

    def test_passed_ci_does_not_promote_paper_ledger_or_production(self):
        pr, checks, paper, artifacts = self.fixtures()
        r = evaluate(pr, checks, paper, artifacts,
                     now=datetime(2026, 11, 10, 13, tzinfo=timezone.utc))
        self.assertTrue(r["code_checks_pass"])
        self.assertFalse(r["paper_ledger_verified"])
        self.assertFalse(r["real_live_execution_enabled"])
        self.assertFalse(r["broker_account_required_for_research"])
        self.assertIn("SCAN_TO_P0R_INTEGRATION_PENDING", r["blockers"])

    def test_failed_ci_and_missing_artifact_fail_closed(self):
        pr, checks, paper, artifacts = self.fixtures()
        checks["check_runs"] = [{"status": "completed", "conclusion": "failure"}]
        r = evaluate(pr, checks, paper, {},
                     now=datetime(2026, 11, 10, 13, tzinfo=timezone.utc))
        self.assertIn("CI_FAILURE", r["blockers"])
        self.assertIn("PAPER_ACCEPTANCE_ARTIFACT_NOT_VERIFIED", r["blockers"])
        self.assertFalse(r["code_checks_pass"])

    def test_retry_only_one_recent_failed_pr_unit_test(self):
        runs = {"workflow_runs": [
            {"name": "P0-R Risk Engine Tests", "head_sha": "abc", "head_branch":
             "research/p0r-failclosed-guards-20261110",
             "event": "pull_request", "status": "completed", "conclusion": "failure",
             "run_attempt": 1, "created_at": datetime.now(timezone.utc).isoformat(),
             "id": 12},
        ]}
        self.assertEqual(safe_retry_candidate(runs, "abc"), 12)
        runs["workflow_runs"][0]["run_attempt"] = 2
        self.assertIsNone(safe_retry_candidate(runs, "abc"))
        runs["workflow_runs"][0]["run_attempt"] = 1
        runs["workflow_runs"][0]["name"] = "Sky Single-Stock Fugle Realtime"
        self.assertIsNone(safe_retry_candidate(runs, "abc"))

    def test_real_schedule_gap_is_not_claimed_five_minute_healthy(self):
        now = datetime(2026, 11, 10, 13, 30, tzinfo=timezone.utc)
        records = {"workflow_runs": [
            {"event": "schedule", "created_at": "2026-11-10T12:27:26Z"},
            {"event": "schedule", "created_at": "2026-11-10T11:33:31Z"},
        ]}
        report = schedule_cadence(records, now=now)
        self.assertEqual(report["status"], "DELAYED_OVER_15_MINUTES")
        self.assertGreater(report["last_interval_minutes"], 50)

    def test_no_schedule_proof_is_unknown_not_success(self):
        self.assertEqual(schedule_cadence({"workflow_runs": []})["status"],
                         "UNKNOWN_NO_SCHEDULE_EVIDENCE")

    def test_recent_five_minute_schedule_proof(self):
        now = datetime(2026, 11, 10, 13, 30, tzinfo=timezone.utc)
        runs = {"workflow_runs": [
            {"event": "schedule", "created_at": "2026-11-10T13:26:00Z"},
            {"event": "schedule", "created_at": "2026-11-10T13:21:00Z"},
        ]}
        self.assertEqual(schedule_cadence(runs, now=now)["status"], "RECENT_SCHEDULE_OBSERVED")

    def test_no_retry_of_mismatched_commit(self):
        runs = {"workflow_runs": [{"name": "P0-R Risk Engine Tests", "head_sha": "wrong",
             "head_branch": "research/p0r-failclosed-guards-20261110", "event": "pull_request",
             "status": "completed", "conclusion": "failure", "run_attempt": 1,
             "created_at": datetime.now(timezone.utc).isoformat(), "id": 12}]}
        self.assertIsNone(safe_retry_candidate(runs, "abc"))


if __name__ == "__main__":
    unittest.main()
