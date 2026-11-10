"""Offline contracts for governed, non-scheduled Sky research self-repair."""
import base64
import unittest
from scripts.sky_governed_auto_repair import safe_patch, review, run, OLD, NEW, ARTIFACT_WARN, ARTIFACT_ERROR, TARGET_BRANCH


class FakeGithub:
    def __init__(self, source):
        self.source = source
        self.calls = []
    def call(self, path, method="GET", body=None):
        self.calls.append((path, method, body))
        if path == "/pulls/511":
            return {"state": "open", "draft": True, "merged": False,
                    "head": {"ref": TARGET_BRANCH, "sha": "abcd1234" * 5}}
        if path.startswith("/contents/") and method == "GET":
            return {"sha": "blob", "content": base64.b64encode(self.source.encode()).decode()}
        if path == "/git/refs" and method == "POST":
            return {}
        if path.startswith("/contents/") and method == "PUT":
            return {}
        if path == "/pulls" and method == "POST":
            return {"html_url": "https://github.com/example/repo/pull/123"}
        raise AssertionError((path, method))


class SafePatchContracts(unittest.TestCase):
    def test_exact_sha_fix(self):
        before = "on:\n  workflow_dispatch:\n" + OLD + "\n"
        after, fixes = safe_patch(before)
        self.assertIn(NEW, after)
        self.assertNotIn(OLD, after)
        self.assertEqual(fixes, ["FIX_BRANCH_SPECIFIC_RECEIPT_SHA_409"])
        self.assertEqual(review(before, after, fixes)["status"], "PASS")

    def test_artifact_fail_closed(self):
        before = "on:\n  workflow_dispatch:\n" + ARTIFACT_WARN + "\n"
        after, fixes = safe_patch(before)
        self.assertIn(ARTIFACT_ERROR, after)
        self.assertEqual(fixes, ["FAIL_CLOSED_MISSING_ARTIFACT"])
        self.assertEqual(review(before, after, fixes)["status"], "PASS")

    def test_combined_patch(self):
        before = "on:\n  workflow_dispatch:\n" + OLD + "\n" + ARTIFACT_WARN + "\n"
        after, fixes = safe_patch(before)
        self.assertEqual(len(fixes), 2)
        self.assertEqual(review(before, after, fixes)["status"], "PASS")

    def test_current_correct_has_no_edit(self):
        before = "on:\n  workflow_dispatch:\n" + NEW + "\n" + ARTIFACT_ERROR
        after, fixes = safe_patch(before)
        self.assertEqual(before, after)
        self.assertEqual(fixes, [])

    def test_ambiguous_patterns_rejected(self):
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_SHA_LOOKUP"):
            safe_patch(OLD + "\n" + OLD)

    def test_review_catches_unapproved_change(self):
        before = "on:\n  workflow_dispatch:\n" + OLD
        after, fixes = safe_patch(before)
        self.assertEqual(review(before, after + "\nproduction_eligible: true", fixes)["status"], "REJECT")

    def test_diagnose_does_not_write(self):
        api = FakeGithub("on:\n  workflow_dispatch:\n" + OLD)
        report = run(api, allow_write=False, event_name="workflow_dispatch")
        self.assertEqual(report["state"], "PATCH_READY_FOR_DRAFT_PR")
        self.assertFalse(any(method != "GET" for _, method, _ in api.calls))

    def test_create_draft_research_pr_only(self):
        api = FakeGithub("on:\n  workflow_dispatch:\n" + OLD)
        report = run(api, allow_write=True, event_name="workflow_run")
        self.assertEqual(report["state"], "DRAFT_REPAIR_PR_CREATED_AWAITING_CI_AND_W0_P0G")
        pr = next(body for path, method, body in api.calls if path == "/pulls" and method == "POST")
        self.assertEqual(pr["base"], TARGET_BRANCH)
        self.assertTrue(pr["draft"])
        self.assertFalse(report["production_eligible"])
        self.assertFalse(report["automatic_order"])

    def test_no_patch_no_writes(self):
        api = FakeGithub("on:\n  workflow_dispatch:\n" + NEW + "\n" + ARTIFACT_ERROR)
        report = run(api, allow_write=True, event_name="workflow_dispatch")
        self.assertEqual(report["state"], "HOLD")
        self.assertFalse(any(method != "GET" for _, method, _ in api.calls))


if __name__ == "__main__":
    unittest.main()
