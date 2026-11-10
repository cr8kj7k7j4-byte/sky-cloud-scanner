"""Contracts for Sky bounded autonomous repair, no network or paid data."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.sky_bounded_auto_repair import decide, normalize_python, run, write_report

SHA = "a" * 40
REPO = "cr8kj7k7j4-byte/sky-cloud-scanner"


def sample():
    event = {
        "action": "completed",
        "workflow_run": {
            "id": 123, "name": "Sky Chat Bridge Unit Checks", "event": "pull_request",
            "conclusion": "failure", "run_attempt": 1, "head_sha": SHA,
            "pull_requests": [{"number": 511}],
        },
    }
    pr = {
        "number": 511, "state": "open", "draft": True,
        "head": {"sha": SHA, "ref": "research/fugle-snapshot-diagnostics-20261110",
                 "repo": {"full_name": REPO}},
    }
    jobs = [{"name": "lint and format", "conclusion": "failure", "id": 8}]
    return event, pr, jobs


class TestSafeRepair(unittest.TestCase):
    def test_formatting_only_preserves_ast(self):
        old = "x = 1   \n# comment   \n"
        self.assertEqual(normalize_python(old), "x = 1\n# comment\n")

    def test_rejects_non_whitespace_program_modification(self):
        # Trailing spaces inside a triple string are semantic Python content.
        self.assertIsNone(normalize_python("x = '''a  \n'''\n"))

    def test_never_fixes_unrelated_failures(self):
        event, pr, _ = sample()
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}):
            decision = decide(event, pr, [{"name": "unit tests", "conclusion": "failure"}])
        self.assertFalse(decision["eligible"])

    def test_rejects_missing_trade_data_and_unknown_pr(self):
        event, pr, jobs = sample()
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}):
            self.assertTrue(decide(event, pr, jobs)["eligible"])
            event["workflow_run"]["pull_requests"] = [{"number": 999}]
            self.assertFalse(decide(event, pr, jobs)["eligible"])

    def test_rejects_fork_and_wrong_sha(self):
        event, pr, jobs = sample()
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}):
            pr["head"]["repo"]["full_name"] = "unknown/fork"
            self.assertFalse(decide(event, pr, jobs)["eligible"])
            pr["head"]["repo"]["full_name"] = REPO
            event["workflow_run"]["head_sha"] = "b" * 40
            self.assertFalse(decide(event, pr, jobs)["eligible"])

    def test_rejects_repeated_attempt_and_unsafe_event(self):
        event, pr, jobs = sample()
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}):
            event["workflow_run"]["run_attempt"] = 2
            self.assertFalse(decide(event, pr, jobs)["eligible"])
            event["workflow_run"]["run_attempt"] = 1
            event["workflow_run"]["event"] = "push"
            self.assertFalse(decide(event, pr, jobs)["eligible"])

    def test_manual_diagnostic_does_not_write(self):
        class ForbiddenAPI:
            def request(self, *_args, **_kwargs):
                self.fail()
        result = run({"action": "manual"}, ForbiddenAPI())
        self.assertEqual(result["status"], "MANUAL_DIAGNOSTIC_ONLY")
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["auto_merge"])

    def test_creates_artifact_with_production_block(self):
        with tempfile.TemporaryDirectory() as td:
            write_report({"checked_at_utc": "2026-11-10T00:00:00+00:00",
                          "status": "DIAGNOSE_ONLY", "self_review": "NOT_RUN"}, Path(td))
            self.assertTrue(Path(td, "latest.md").exists())
            self.assertEqual(json.loads(Path(td, "latest.json").read_text())["status"],
                             "DIAGNOSE_ONLY")


if __name__ == "__main__":
    unittest.main()
