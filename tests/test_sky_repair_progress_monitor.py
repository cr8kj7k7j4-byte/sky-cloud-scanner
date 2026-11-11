import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from research.sky_repair_progress_monitor import (
    collect, http_get_json, summarize, write_report, TARGET_PRS,
)

SHA = "a" * 40


def pr(number=511, draft=True):
    return {
        "number": number, "title": "Research", "state": "open",
        "draft": draft, "html_url": "https://github.com/example/repo/pull/" + str(number),
        "head": {"sha": SHA}, "updated_at": "2026-11-10T13:00:00Z",
    }


def run(conclusion="success", status="completed", sha=SHA):
    return {"head_sha": sha, "status": status, "conclusion": conclusion}


class RepairProgressTests(unittest.TestCase):
    def test_latest_head_green_ci_still_requires_acceptance(self):
        obj = summarize(pr(), [run(), run("failure", sha="b" * 40)])
        self.assertEqual(obj["status"], "CI_GREEN_DRAFT_REQUIRES_ACCEPTANCE")
        self.assertEqual(obj["ci_failure"], 0)
        self.assertFalse(obj["production_promotion"])

    def test_failure_and_active(self):
        self.assertEqual(summarize(pr(), [run("failure")])["status"], "CI_FAILED_NEEDS_ENGINEERING")
        self.assertEqual(summarize(pr(), [run(None, "in_progress")])["status"], "CI_IN_PROGRESS")

    def test_empty_ci_fails_closed(self):
        self.assertEqual(summarize(pr(), [])["status"], "NO_LATEST_HEAD_CI_EVIDENCE")

    def test_bounded_reads_and_artifacts(self):
        calls = []

        def fake(path):
            calls.append(path)
            if path.startswith("pulls/"):
                return pr(int(path.split("/")[1]))
            return {"workflow_runs": [run()]}

        obj = collect(fake, datetime(2026, 11, 10, tzinfo=timezone.utc))
        self.assertEqual(len(calls), len(TARGET_PRS) * 2)
        self.assertEqual(obj["health"], "CI_FINISHED_ACCEPTANCE_PENDING")
        self.assertFalse(obj["production_eligible"])
        with tempfile.TemporaryDirectory() as folder:
            write_report(obj, Path(folder))
            self.assertEqual(json.loads((Path(folder) / "latest.json").read_text())["schema"],
                             "SKY_W0_REPAIR_PROGRESS_V1")
            self.assertIn("#511", (Path(folder) / "latest.md").read_text())

    def test_read_failure_is_not_silent(self):
        def fake(path):
            if path == "pulls/506":
                raise urllib.error.HTTPError("url", 403, "forbidden", {}, None)
            if path.startswith("pulls/"):
                return pr(int(path.split("/")[1]))
            return {"workflow_runs": [run()]}
        obj = collect(fake)
        self.assertEqual(obj["health"], "BLOCKED_NEEDS_HUMAN_ENGINEERING")
        self.assertEqual(obj["fetch_errors"][0]["pr"], 506)

    def test_transient_get_retries_only_get_and_caps_at_three_attempts(self):
        count = [0]
        class Response:
            def __enter__(self): return self
            def __exit__(self, *unused): return False
            def read(self): return b'{"ok":true}'
        def fake(req, timeout):
            self.assertEqual(req.get_method(), "GET")
            count[0] += 1
            if count[0] < 3:
                raise urllib.error.HTTPError("url", 503, "busy", {}, None)
            return Response()
        sleeps = []
        self.assertTrue(http_get_json("https://api.github.com/test", "token", fake, sleeps.append)["ok"])
        self.assertEqual(sleeps, [1, 2])


if __name__ == "__main__":
    unittest.main()
