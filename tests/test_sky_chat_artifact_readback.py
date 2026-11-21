"""Offline regression tests for external downloaded ZIP contents."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.sky_chat_artifact_readback import verify_download
from src.sky_chat_bridge import COLUMNS

NOW = datetime(2026, 11, 11, 3, 0, tzinfo=timezone.utc)
RUN = "123456"
REQ = "chat-test-1234"
SHA = "a" * 40


def payload():
    status = {
        "schema": "SKY_CHAT_SCAN_STATUS_V1",
        "scan_id": RUN, "request_id": REQ,
        "head_sha": SHA,
        "run_url": "https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/" + RUN,
        "completed_at_utc": (NOW - timedelta(seconds=20)).isoformat(),
        "data_timestamp": (NOW - timedelta(seconds=40)).isoformat(),
        "status": "REPORT_READY_RESEARCH_ONLY", "source": "FUGLE_PAID_SNAPSHOT",
        "row_count": 1, "universe_count": 1, "observed_price_count": 1,
        "stage2_verified_executed_count": 0,
        "production_eligible": False, "automatic_order": False,
    }
    row = {c: "待確認" for c in COLUMNS}
    row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
    report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
              "rows": [row], "row_count": 1, "universe_count": 1,
              "checked_at_tpe": status["data_timestamp"],
              "production_eligible": False}
    return status, report


class ArtifactReadbackTests(unittest.TestCase):
    def check(self, change=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "chat_bridge").mkdir()
            (root / "sky_quickscan_information").mkdir()
            status, report = payload()
            if change:
                change(status, report)
            (root / "chat_bridge/latest.json").write_text(json.dumps(status), encoding="utf-8")
            (root / "sky_quickscan_information/latest_13col.json").write_text(json.dumps(report), encoding="utf-8")
            return verify_download(root, run_id=RUN, request_id=REQ, head_sha=SHA,
                                   expected_sha=SHA, artifact_id="456789", now=NOW)

    def test_valid_research_readback(self):
        receipt = self.check()
        self.assertEqual(receipt["status"], "PASS_RESEARCH_ONLY")
        self.assertEqual(receipt["row_count"], 1)
        self.assertFalse(receipt["production_eligible"])

    def test_wrong_run_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "RUN_HEAD_SHA_MISMATCH"):
            with tempfile.TemporaryDirectory() as td:
                verify_download(Path(td), run_id=RUN, request_id=REQ,
                                head_sha=SHA, expected_sha="b" * 40,
                                artifact_id="1", now=NOW)

    def test_downloaded_status_wrong_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "DOWNLOADED_STATUS_SHA_MISMATCH"):
            self.check(lambda status, report: status.update(head_sha="b" * 40))

    def test_downloaded_status_missing_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "DOWNLOADED_STATUS_SHA_MISMATCH"):
            self.check(lambda status, report: status.pop("head_sha"))

    def test_wrong_request_rejected(self):
        with self.assertRaisesRegex(ValueError, "REQUEST_ID_MISMATCH"):
            self.check(lambda status, report: status.update(request_id="wrong"))

    def test_stale_capture_rejected(self):
        with self.assertRaisesRegex(ValueError, "STALE_SNAPSHOT_CAPTURE"):
            self.check(lambda status, report: status.update(
                data_timestamp=(NOW - timedelta(hours=1)).isoformat()))

    def test_mixed_report_capture_time_rejected(self):
        with self.assertRaisesRegex(ValueError, "REPORT_CAPTURE_TIMESTAMP_MISMATCH"):
            self.check(lambda status, report: report.update(
                checked_at_tpe=(NOW - timedelta(minutes=3)).isoformat()))

    def test_missing_report_capture_time_rejected(self):
        with self.assertRaisesRegex(ValueError, "REPORT_CAPTURE_TIMESTAMP_MISMATCH"):
            self.check(lambda status, report: report.pop("checked_at_tpe"))

    def test_missing_column_rejected(self):
        with self.assertRaisesRegex(ValueError, "REPORT_MISSING_13_COLUMNS"):
            self.check(lambda status, report: report["rows"][0].pop("停利價格"))

    def test_buy_action_rejected(self):
        with self.assertRaisesRegex(ValueError, "REPORT_TRADE_GATE_VIOLATION"):
            self.check(lambda status, report: report["rows"][0].update(現在動作="買進"))


if __name__ == "__main__":
    unittest.main()
