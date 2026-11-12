import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from research.sky_repair_progress_monitor import (
    collect, http_get_json, summarize, write_report, route_work_items, TARGET_PRS,
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
        self.assertEqual(obj["watchdog_cadence"], "10_MINUTES_BEST_EFFORT_GITHUB_ACTIONS")
        self.assertEqual(obj["monitored_prs"], [508, 511, 512, 531, 536])
        self.assertEqual(obj["details"][1]["work_window"], "MARKET_SESSION")
        self.assertFalse(obj["details"][0]["repair_performed"])
        self.assertFalse(obj["production_eligible"])
        with tempfile.TemporaryDirectory() as folder:
            write_report(obj, Path(folder))
            self.assertEqual(json.loads((Path(folder) / "latest.json").read_text())["schema"],
                             "SKY_W0_REPAIR_PROGRESS_V1")
            self.assertIn("#511", (Path(folder) / "latest.md").read_text())

    def test_read_failure_is_not_silent(self):
        def fake(path):
            if path == "pulls/508":
                raise urllib.error.HTTPError("url", 403, "forbidden", {}, None)
            if path.startswith("pulls/"):
                return pr(int(path.split("/")[1]))
            return {"workflow_runs": [run()]}
        obj = collect(fake)
        self.assertEqual(obj["health"], "BLOCKED_NEEDS_HUMAN_ENGINEERING")
        self.assertEqual(obj["fetch_errors"][0]["pr"], 508)


    def test_operator_blocker_does_not_stop_unrelated_off_market_repairs(self):
        details = [summarize(pr(n), [run()]) for n in TARGET_PRS]
        now = datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc)
        work = route_work_items(details, now, {
            508: {"action": "Owner must approve external source permission",
                  "url": "https://github.com/example/repo/settings"}})
        states = {x["pr"]: x["routing_state"] for x in work["queue"]}
        self.assertEqual(states[508], "WAIT_USER")
        self.assertEqual(states[511], "WAIT_MARKET")
        self.assertEqual(states[531], "READY_FOR_ENGINEERING")
        self.assertEqual(states[536], "READY_FOR_ENGINEERING")
        self.assertNotIn(508, work["next_off_market_engineering_prs"])
        self.assertIn(531, work["next_off_market_engineering_prs"])
        self.assertEqual(work["operator_notifications"][0]["pr"], 508)
        self.assertFalse(work["official_trading_day_confirmed"])

    def test_market_clock_is_not_official_market_authorization(self):
        details = [summarize(pr(511), [run()]),
                   summarize(pr(536), [run()])]
        work = route_work_items(details,
                               datetime(2026, 11, 13, 1, 5, tzinfo=timezone.utc))
        self.assertTrue(work["session_clock_only"])
        self.assertEqual(work["queue"][0]["routing_state"],
                         "WAIT_OFFICIAL_MARKET_CONFIRMATION")
        self.assertEqual(work["queue"][1]["routing_state"], "DEFER_TO_OFF_MARKET")
        self.assertFalse(work["official_trading_day_confirmed"])

    def test_operator_blocker_needs_explicit_action_and_url(self):
        details = [summarize(pr(508), [run()])]
        with self.assertRaises(ValueError):
            route_work_items(details, datetime.now(timezone.utc),
                             {508: {"action": "needs owner"}})

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
