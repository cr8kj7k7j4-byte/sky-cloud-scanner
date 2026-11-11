import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from research.sky_w0_dedup_inventory import (
    audit, _cron_from_workflow, RETAIN_PROTECTED, REMOVED,
)


class RepoDedupInventoryTest(unittest.TestCase):
    def test_cron_overlap_is_not_paid_api_cost_evidence(self):
        x = _cron_from_workflow('name: a\non:\n  schedule:\n    - cron: "*/5 1 * * 1-5"\n    - cron: "5 2 * * 1-5"\n  workflow_dispatch:')
        self.assertEqual(x, ["*/5 1 * * 1-5", "5 2 * * 1-5"])

    def test_manual_only_workflow_has_no_schedule(self):
        self.assertEqual(_cron_from_workflow("name: x\non:\n  workflow_dispatch:\njobs:"), [])

    def test_all_workflow_paths_scanned_without_pretending_delete_safe(self):
        result = audit()
        self.assertGreater(result["workflow_count"], 100)
        self.assertTrue(result["overlapping_cron_not_equal_paid_api_duplication"])
        self.assertFalse(result["safe_bulk_delete_ready"])
        self.assertFalse(result["live_trading_enabled"])
        self.assertFalse(result["broker_account_required_for_research"])
        self.assertEqual(result["protected_workflows_missing"], [])
        self.assertEqual(result["removed_workflows_resurrected"], [])
        self.assertEqual(result["expired_watchdog_crons_reintroduced"], [])
        self.assertEqual(result["verdict"], "HOLD_MANUAL_DEPENDENCY_REVIEW_REQUIRED")

    def test_independent_paid_manual_and_push_are_not_certified_deduplicated(self):
        from research.sky_w0_dedup_inventory import paid_workflow_overlap
        rows = [
            {"name": "sky-chat.yml", "paid_fugle_secret_referenced": True,
             "manual_dispatch": True, "push_trigger": True,
             "schedule_cron": [], "concurrency_group": "chat"},
            {"name": "sky-private.yml", "paid_fugle_secret_referenced": True,
             "manual_dispatch": True, "push_trigger": False,
             "schedule_cron": [], "concurrency_group": None},
            {"name": "sky-offline.yml", "paid_fugle_secret_referenced": False,
             "manual_dispatch": True, "push_trigger": True,
             "schedule_cron": [], "concurrency_group": "chat"},
        ]
        out = paid_workflow_overlap(rows)
        self.assertEqual(out["paid_workflow_count"], 2)
        self.assertEqual(out["scheduled_paid_entrypoints"], [])
        self.assertEqual(out["manual_paid_entrypoints"],
                         ["sky-chat.yml", "sky-private.yml"])
        self.assertEqual(out["push_paid_entrypoints"], ["sky-chat.yml"])
        self.assertFalse(out["cross_workflow_paid_api_dedup_certified"])
        self.assertFalse(out["runtime_paid_api_lease_verified"])
        self.assertFalse(out["provider_request_id_reconciliation_verified"])
        self.assertIn("HOLD_", out["status"])

    def test_paid_workflow_audit_never_infers_actual_duplicate_charges(self):
        from research.sky_w0_dedup_inventory import paid_workflow_overlap
        out = paid_workflow_overlap([{
            "name": "x.yml", "paid_fugle_secret_referenced": True,
            "manual_dispatch": False, "push_trigger": False,
            "schedule_cron": [], "concurrency_group": None,
        }])
        self.assertEqual(out["status"], "INSUFFICIENT_RUNTIME_EVIDENCE")
        self.assertFalse(out["cross_workflow_paid_api_dedup_certified"])

    def test_synthetic_duplicate_cron_reports_overlap_not_paid_use(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            wf = root / ".github/workflows"
            wf.mkdir(parents=True)
            for filename in ("a.yml", "b.yml"):
                (wf / filename).write_text(
                    "on:\n  schedule:\n    - cron: '*/5 1 * * 1-5'\n",
                    encoding="utf-8")
            result = audit(root)
            self.assertEqual(result["workflow_count"], 2)
            self.assertEqual(len(result["potential_overlapping_cron_groups"]), 1)
            self.assertTrue(result["overlapping_cron_not_equal_paid_api_duplication"])
            self.assertEqual(result["open_pr_api_status"], "PR_METADATA_NOT_QUERIED")


if __name__ == "__main__":
    unittest.main()
