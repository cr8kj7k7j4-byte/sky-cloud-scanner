import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo
from pathlib import Path
from tempfile import TemporaryDirectory

from research.sky_full_universe_information import build
from scripts.sky_alert_chat_readback import make_receipt, select_source, find_source_json

TZ = ZoneInfo("Asia/Taipei")


class SkyAlertChatReadbackTests(unittest.TestCase):
    def test_readonly_existing_artifact_preserves_no_trade(self):
        now = datetime(2026, 11, 23, 12, 45, tzinfo=TZ)
        report = build(
            [{"symbol": "1234", "name": "Example", "exchange": "TWSE"}],
            {"TSE": {"date": now.date().isoformat(), "data": [{
                "symbol": "1234", "lastPrice": 50, "tradeVolume": 1000
            }]}},
            now,
        )
        with patch("scripts.sky_alert_chat_readback.consume") as consume:
            from research.sky_alert_reader import consume as real_consume
            consume.side_effect = lambda source: real_consume(source, now=now)
            result = make_receipt(report, run_id="45112399999", run_attempt="1",
                                  head_sha="a" * 40, comment_id="7090000000",
                                  source_provenance={"source_run_id": "45112352453"})
        self.assertEqual(result["freshness_status"], "NO_VERIFIED_EXECUTIONS")
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["automatic_order"])
        self.assertEqual(result["trade_action"], "禁止交易")

    def test_source_selection_excludes_current_run_and_requires_matching_artifact(self):
        runs = [{"id": 200, "conclusion": "success", "event": "issue_comment", "run_attempt": 1,
                 "head_sha": "a" * 40},
                {"id": 199, "conclusion": "success", "event": "issue_comment", "run_attempt": 1,
                 "head_sha": "b" * 40}]
        with patch("scripts.sky_alert_chat_readback.gh_json") as gh:
            gh.side_effect = [
                {"workflow_runs": runs},
                {"artifacts": [{"id": 34, "name": "sky-chat-199-attempt-1", "expired": False}]}
            ]
            run, artifact = select_source(current_run_id="200")
        self.assertEqual(run["id"], 199)
        self.assertEqual(artifact["id"], 34)

    def test_no_verified_source_is_blocked(self):
        with patch("scripts.sky_alert_chat_readback.gh_json", return_value={"workflow_runs": []}):
            with self.assertRaisesRegex(ValueError, "NO_VERIFIED_EXISTING_SCAN_ARTIFACT"):
                select_source(current_run_id="1")

    def test_artifact_relative_layout_is_resolved_without_guessing_other_files(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "sky_quickscan_information" / "full_universe.json"
            path.parent.mkdir()
            path.write_text("{}", encoding="utf-8")
            self.assertEqual(find_source_json(root), path)
            alt = root / "full_universe.json"
            alt.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "AMBIGUOUS"):
                find_source_json(root)

    def test_existing_workflow_only_owner_alert_job_never_paid(self):
        workflow = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        scan, alert = workflow.split("\n  alert_readonly:", 1)
        self.assertIn("github.event.comment.body != 'Sky 警戒'", scan)
        for item in ("github.event.issue.number == 363",
                     "github.event.comment.user.login == github.repository_owner",
                     "github.event.comment.author_association == 'OWNER'",
                     "github.event.comment.body == 'Sky 警戒'"):
            self.assertIn(item, alert)
        self.assertNotIn("FUGLE_API_KEY", alert)
        self.assertNotIn("sky_paid_fugle_api_guard", alert)
        self.assertIn("scripts.sky_alert_chat_readback", alert)
        self.assertIn("sky-alert-external-readback-", alert)


if __name__ == "__main__":
    unittest.main()
