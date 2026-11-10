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
        self.repo = "test/repo"
        self.calls = []
    def call(self, path, method="GET", body=None):
        self.calls.append((path, method, body))
        if path == "/pulls/511":
            return {"state": "open", "draft": True, "merged": False,
                    "head": {"ref": TARGET_BRANCH, "sha": "abcd1234" * 5,
                             "repo": {"full_name": "test/repo"}}}
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

    def test_source_is_pinned_to_immutable_sha(self):
        api = FakeGithub("on:\n  workflow_dispatch:\n" + OLD)
        result = run(api, allow_write=False, event_name="workflow_dispatch")
        self.assertEqual(result["state"], "PATCH_READY_FOR_DRAFT_PR")
        reads = [path for path, method, _ in api.calls
                 if method == "GET" and path.startswith("/contents/")]
        self.assertEqual(len(reads), 1)
        self.assertTrue(reads[0].endswith("?ref=" + "abcd1234" * 5))

    def test_pr_head_changed_during_diagnosis_does_not_write(self):
        class AdvancingGithub(FakeGithub):
            def __init__(self, source):
                super().__init__(source)
                self.pr_reads = 0
            def call(self, path, method="GET", body=None):
                if path == "/pulls/511" and method == "GET":
                    self.calls.append((path, method, body))
                    self.pr_reads += 1
                    current = ("abcd1234" * 5 if self.pr_reads == 1
                               else "new_sha_is_not_the_original")
                    return {"state": "open", "draft": True, "merged": False,
                            "head": {"ref": TARGET_BRANCH, "sha": current,
                                     "repo": {"full_name": "test/repo"}}}
                return super().call(path, method, body)
        api = AdvancingGithub("on:\n  workflow_dispatch:\n" + OLD)
        result = run(api, allow_write=True, event_name="workflow_run",
                     expected_sha="abcd1234" * 5)
        self.assertEqual(result["state"], "HOLD")
        self.assertIn("TARGET_PR_HEAD_CHANGED_BEFORE_PATCH", result["blockers"])
        self.assertFalse(any(method != "GET" for _, method, _ in api.calls))

    def test_foreign_repository_pr_is_rejected_without_writes(self):
        class ForeignPRGithub(FakeGithub):
            def call(self, path, method="GET", body=None):
                response = super().call(path, method, body)
                if path == "/pulls/511" and method == "GET":
                    response["head"]["repo"]["full_name"] = "untrusted/fork"
                return response

        api = ForeignPRGithub("on:\\n  workflow_dispatch:\\n" + OLD)
        report = run(api, allow_write=True, event_name="workflow_run",
                     expected_sha="abcd1234" * 5)
        self.assertEqual(report["state"], "HOLD")
        self.assertIn("TARGET_REPOSITORY_NOT_TRUSTED", report["blockers"])
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
                "repository": {"full_name": "test/repo"},
                "head_repository": {"full_name": "test/repo"},
                "event": "pull_request",
                "conclusion": "failure",
                "run_attempt": 1,
                "head_sha": "abcd1234" * 5,
                "head_branch": TARGET_BRANCH,
                "path": ".github/workflows/sky-chat-bridge-tests.yml",
                "pull_requests": [{"number": 511}],
            },
        }
        bad_cases = [
            {"pull_requests": [{"number": 512}]},
            {"pull_requests": [{"number": 512}, {"number": 511}]},
            {"head_branch": "untrusted-research"},
            {"path": ".github/workflows/other-ci.yml"},
            {"event": "push"},
            {"run_attempt": 2},
            {"run_attempt": None},
            {"run_attempt": 0},
            {"run_attempt": False},
            {"run_attempt": "1"},
            {"run_attempt": "invalid"},
            {"head_sha": ""},
            {"repository": {"full_name": "foreign/repo"}},
            {"head_repository": {"full_name": "foreign/repo"}},
            {"repository": None},
            {"head_repository": None},
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


    def test_empty_pr_links_can_recover_only_pinned_target_sha(self):
        """GitHub legitimately returns pull_requests=[] for some PR workflow runs."""
        payload = {
            "action": "completed",
            "workflow_run": {
                "name": "Sky Chat Bridge Unit Checks",
                "repository": {"full_name": "test/repo"},
                "head_repository": {"full_name": "test/repo"},
                "event": "pull_request",
                "conclusion": "failure",
                "run_attempt": 1,
                "head_sha": "abcd1234" * 5,
                "head_branch": TARGET_BRANCH,
                "path": ".github/workflows/sky-chat-bridge-tests.yml",
                "pull_requests": [],
            },
        }
        with tempfile.TemporaryDirectory() as folder:
            event_file = Path(folder, "event.json")
            event_file.write_text(json.dumps(payload), encoding="utf-8")
            api = FakeGithub("on:\\n  workflow_dispatch:\\n" + OLD)
            with patch.dict(os.environ, {
                "GITHUB_EVENT_NAME": "workflow_run",
                "GITHUB_EVENT_PATH": str(event_file),
                "GITHUB_REPOSITORY": "test/repo",
                "GH_TOKEN": "offline-fixture",
                "SKY_APPROVED_SAFE_PATCH": "true",
            }), patch.object(governed, "OUTPUT", Path(folder, "latest.json")), \
                 patch.object(governed, "Github", return_value=api):
                self.assertEqual(governed.main(), 0)
            result = json.loads(Path(folder, "latest.json").read_text())
            self.assertEqual(result["state"], "DRAFT_REPAIR_PR_CREATED_AWAITING_CI_AND_W0_P0G")
            self.assertEqual(result["target_sha"], "abcd1234" * 5)
            self.assertEqual(result["self_review"]["status"], "PASS")

    def test_valid_same_sha_failure_event_creates_draft_in_offline_contract(self):
        """Simulated GitHub event only: must not be mistaken for real Actions E2E."""
        payload = {
            "action": "completed",
            "workflow_run": {
                "name": "Sky Chat Bridge Unit Checks",
                "repository": {"full_name": "test/repo"},
                "head_repository": {"full_name": "test/repo"},
                "event": "pull_request",
                "conclusion": "failure",
                "run_attempt": 1,
                "head_sha": "abcd1234" * 5,
                "head_branch": TARGET_BRANCH,
                "path": ".github/workflows/sky-chat-bridge-tests.yml",
                "pull_requests": [{"number": 511}],
            },
        }
        with tempfile.TemporaryDirectory() as folder:
            event_file = Path(folder, "event.json")
            event_file.write_text(json.dumps(payload), encoding="utf-8")
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
            result = json.loads(Path(folder, "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(result["state"], "DRAFT_REPAIR_PR_CREATED_AWAITING_CI_AND_W0_P0G")
            self.assertEqual(result["repair_pr"], "https://github.com/example/repo/pull/123")
            self.assertEqual(result["self_review"]["status"], "PASS")
            self.assertFalse(result["production_eligible"])
            self.assertFalse(result["automatic_merge"])
            self.assertEqual(len([call for call in api.calls if call[1] != "GET"]), 3)
            created = next(body for path, method, body in api.calls
                           if path == "/pulls" and method == "POST")
            self.assertEqual(created["base"], TARGET_BRANCH)
            self.assertTrue(created["draft"])
            self.assertFalse(any(path == "/merges" for path, _, _ in api.calls))


if __name__ == "__main__":
    unittest.main()
