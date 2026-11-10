"""Offline contracts for governed, non-scheduled Sky research self-repair."""
import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import scripts.sky_governed_auto_repair as governed
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

    def test_stale_ci_sha_never_writes(self):
        api = FakeGithub("on:\\n  workflow_dispatch:\\n" + OLD)
        report = run(api, allow_write=True, event_name="workflow_run",
                     expected_sha="different-latest-sha")
        self.assertEqual(report["state"], "HOLD")
        self.assertIn("TRIGGER_SHA_NOT_CURRENT_PR_HEAD", report["blockers"])
        self.assertFalse(any(method != "GET" for _, method, _ in api.calls))

    def test_unrelated_or_replayed_ci_event_is_diagnose_only(self):
        base = {
            "action": "completed",
            "workflow_run": {
                "name": "Sky Chat Bridge Unit Checks",
                "event": "pull_request",
                "conclusion": "failure",
                "run_attempt": 1,
                "head_sha": "abcd1234" * 5,
                "pull_requests": [{"number": 511}],
            },
        }
        bad_cases = [
            {"pull_requests": [{"number": 512}]},
            {"pull_requests": []},
            {"event": "push"},
            {"run_attempt": 2},
            {"run_attempt": None},
            {"run_attempt": 0},
            {"run_attempt": False},
            {"run_attempt": "1"},
            {"run_attempt": "invalid"},
            {"head_sha": ""},
        ]
        for diff in bad_cases:
            with self.subTest(diff=diff):
                payload = json.loads(json.dumps(base))
                payload["workflow_run"].update(diff)
                with tempfile.TemporaryDirectory() as folder:
                    event_file = Path(folder, "event.json")
                    event_file.write_text(json.dumps(payload))
                    api = FakeGithub("on:\\n  workflow_dispatch:\\n" + OLD)
                    with patch.dict(os.environ, {
                        "GITHUB_EVENT_NAME": "workflow_run",
                        "GITHUB_EVENT_PATH": str(event_file),
                        "GITHUB_REPOSITORY": "test/repo",
                        "GH_TOKEN": "offline-fixture",
                        "SKY_APPROVED_SAFE_PATCH": "true",
                    }), patch.object(governed, "OUTPUT", Path(folder, "latest.json")), \
                         patch.object(governed, "Github", return_value=api):
                        code = governed.main()
                    self.assertEqual(code, 0)
                    result = json.loads(Path(folder, "latest.json").read_text())
                    self.assertEqual(result["state"], "NOT_APPLICABLE")
                    self.assertFalse(api.calls)


if __name__ == "__main__":
    unittest.main()
