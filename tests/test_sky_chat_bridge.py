import unittest
from src.sky_chat_bridge import COLUMNS, make_status, validate_report, validate_request

class ChatScanBridgeTests(unittest.TestCase):
    def test_external_artifact_readback_requires_downloaded_evidence(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        validator = (Path(__file__).resolve().parents[1] /
                     "scripts/sky_chat_artifact_readback.py").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("  actions: read"), 1)
        self.assertEqual(workflow.count("uses: actions/download-artifact@v4"), 1)
        self.assertIn("steps.main_artifact_upload.outputs.artifact-id", workflow)
        self.assertIn("steps.same_run_download.outcome == 'success'", workflow)
        self.assertIn("EXPECTED_ARTIFACT_ID: ${{ steps.main_artifact_upload.outputs.artifact-id }}", workflow)
        self.assertIn('str(receipt.get("artifact_id")) == os.environ.get("EXPECTED_ARTIFACT_ID")', workflow)
        self.assertIn('receipt.get("row_count") == data.get("row_count")', workflow)
        self.assertIn('receipt.get("production_eligible") is False', workflow)
        self.assertIn('receipt.get("automatic_order") is False', workflow)
        self.assertIn('receipt.get("trade_action") == "禁止交易"', workflow)
        self.assertNotIn('gh run download "$GITHUB_RUN_ID"', workflow)
        self.assertIn('--head-sha "$HEAD_SHA" --expected-sha "$GITHUB_SHA"', workflow)
        self.assertIn("sky-chat-external-readback-", workflow)
        self.assertIn('root / "chat_bridge/latest.json"', validator)
        self.assertIn('root / "sky_quickscan_information/latest_13col.json"', validator)
        self.assertIn("RUN_HEAD_SHA_MISMATCH", validator)
        self.assertIn("REPORT_DUPLICATE_OR_MISSING_SYMBOL", validator)
        self.assertIn("ARTIFACT_ID_MISSING", validator)

    def test_cancelled_bridge_preserves_fail_closed_diagnostic(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        self.assertIn('bridge_outcome == "cancelled"', workflow)
        self.assertIn('"DATA_BLOCKED_BRIDGE_CANCELLED"', workflow)
        self.assertIn('"BRIDGE_JOB_CANCELLED"', workflow)
        self.assertIn('data["bridge_step_outcome"] = bridge_outcome', workflow)
        self.assertIn('if not valid or bridge_outcome != "success"', workflow)
        self.assertIn('data["production_eligible"] = False', workflow)
        self.assertIn('data["automatic_order"] = False', workflow)

    def test_cancelled_bridge_writes_fail_closed_diagnostic(self):
        import os
        import re
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        match = re.search(
            r"      - name: Verify status and preserve a failed-run diagnostic\n"
            r".*?          python - <<'PY'\n"
            r"(.*?)\n          PY\n"
            r"      - name: Upload complete", workflow, re.S)
        self.assertIsNotNone(match, "Bridge diagnostic guard missing")
        guard = "\n".join(line[10:] if line.startswith("          ") else line
                          for line in match.group(1).splitlines())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "output/chat_bridge/latest.json"
            env = dict(os.environ, GITHUB_RUN_ID="123456", BRIDGE_OUTCOME="cancelled")
            result = subprocess.run([sys.executable, "-c", guard], cwd=tmp,
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            data = __import__("json").loads(target.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "DATA_BLOCKED_BRIDGE_CANCELLED")
            self.assertEqual(data["block_reason"], "BRIDGE_JOB_CANCELLED")
            self.assertFalse(data["production_eligible"])
            self.assertFalse(data["automatic_order"])

    def test_main_status_publish_guard_executes_fail_closed(self):
        import json
        import os
        import re
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        match = re.search(
            r"      - name: Publish sanitized summary for ChatGPT GitHub connector\n"
            r".*?          python - <<'PY'\n"
            r"(.*?)\n          PY\n", workflow, re.S)
        self.assertIsNotNone(match, "Published-status verification script missing")
        guard = "\n".join(line[10:] if line.startswith("          ") else line
                          for line in match.group(1).splitlines())
        for download, upload, receipt_status, tamper, should_pass in (
            ("success", "failure", "PASS_RESEARCH_ONLY", None, False),
            ("failure", "success", "PASS_RESEARCH_ONLY", None, False),
            ("success", "success", "FAILED_CLOSED", None, False),
            ("success", "success", "PASS_RESEARCH_ONLY", "artifact_id", False),
            ("success", "success", "PASS_RESEARCH_ONLY", "row_count", False),
            ("success", "success", "PASS_RESEARCH_ONLY", "trade_action", False),
            ("success", "success", "PASS_RESEARCH_ONLY", "automatic_order", False),
            ("success", "success", "PASS_RESEARCH_ONLY", None, True),
        ):
            with self.subTest(download=download, upload=upload, receipt=receipt_status,
                              tamper=tamper):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    (root / "output/chat_bridge").mkdir(parents=True)
                    (root / "output/chat_bridge_readback").mkdir(parents=True)
                    status = {"schema": "SKY_CHAT_SCAN_STATUS_V1",
                              "status": "REPORT_READY_RESEARCH_ONLY",
                              "scan_id": "123456", "request_id": "req-123",
                              "row_count": 1986,
                              "production_eligible": False, "automatic_order": False}
                    receipt = {"status": receipt_status, "run_id": "123456",
                               "head_sha": "a" * 40, "request_id": "req-123",
                               "artifact_id": "123", "row_count": 1986,
                               "trade_action": "禁止交易",
                               "production_eligible": False, "automatic_order": False}
                    if tamper == "artifact_id":
                        receipt["artifact_id"] = "wrong"
                    elif tamper == "row_count":
                        receipt["row_count"] = 1985
                    elif tamper == "trade_action":
                        receipt["trade_action"] = "買進"
                    elif tamper == "automatic_order":
                        receipt["automatic_order"] = True
                    (root / "output/chat_bridge/latest.json").write_text(
                        json.dumps(status), encoding="utf-8")
                    (root / "output/chat_bridge_readback/external_receipt.json").write_text(
                        json.dumps(receipt), encoding="utf-8")
                    env = dict(os.environ, GITHUB_RUN_ID="123456",
                               GITHUB_SHA="a" * 40, EXPECTED_ARTIFACT_ID="123",
                               EXTERNAL_READBACK_OUTCOME=download,
                               EXTERNAL_RECEIPT_UPLOAD_OUTCOME=upload)
                    result = subprocess.run([sys.executable, "-c", guard],
                                            cwd=tmp, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    published = json.loads(Path("/tmp/sky-chat-status.json").read_text(encoding="utf-8"))
                    self.assertIs(published["external_readback_verified"], should_pass)
                    self.assertFalse(published["production_eligible"])
                    self.assertFalse(published["automatic_order"])
                    if should_pass:
                        self.assertEqual(published["status"], "REPORT_READY_RESEARCH_ONLY")
                    else:
                        self.assertEqual(published["status"], "DATA_BLOCKED_EXTERNAL_READBACK")
                        self.assertEqual(published["readback"]["trade_action"], "禁止交易")

    def test_research_branch_scan_cannot_publish_main_status(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        publish_step = workflow.split("- name: Publish sanitized summary for ChatGPT GitHub connector", 1)[1]
        self.assertIn("if: ${{ always() && github.ref == 'refs/heads/main' }}", publish_step)
        self.assertIn("if: always()", workflow.split("- name: Upload complete 13-column report and status", 1)[1].split("- name: Publish sanitized summary", 1)[0])

    def test_request_good(self):
        self.assertEqual(validate_request({"command":"Sky 當沖現在掃一次","request_id":"chat-20261109-a","read_only_no_orders":True}),"chat-20261109-a")

    def test_quickscan_alias_same_read_only_research_bridge(self):
        self.assertEqual(validate_request({
            "command": "Sky 快掃",
            "request_id": "chat-20261110-quickscan-001",
            "read_only_no_orders": True,
        }), "chat-20261110-quickscan-001")
        with self.assertRaisesRegex(ValueError, "ORDER_POLICY_REQUIRED"):
            validate_request({
                "command": "Sky 快掃",
                "request_id": "chat-20261110-quickscan-002",
                "read_only_no_orders": False,
            })

    def test_all_five_aliases_route_to_existing_bridge(self):
        from src.sky_scan_readback import COMMANDS, canonical_command
        self.assertEqual(len(COMMANDS), 5)
        for alias in COMMANDS:
            with self.subTest(alias=alias):
                self.assertEqual(canonical_command(alias), "Sky 快掃")
                self.assertEqual(validate_request({
                    "command": alias, "request_id": "chat-alias-20261111",
                    "read_only_no_orders": True}), "chat-alias-20261111")
                with self.assertRaisesRegex(ValueError, "ORDER_POLICY_REQUIRED"):
                    validate_request({
                        "command": alias, "request_id": "chat-alias-20261111",
                        "read_only_no_orders": False})

    def test_request_denies_order(self):
        with self.assertRaisesRegex(ValueError,"ORDER_POLICY_REQUIRED"):
            validate_request({"command":"Sky 當沖現在掃一次","request_id":"chat-20261109-a","read_only_no_orders":False})

    def test_request_rejects_unsafe_id(self):
        with self.assertRaisesRegex(ValueError,"UNSAFE_REQUEST_ID"):
            validate_request({"command":"Sky 當沖現在掃一次","request_id":"../../../../../tmp","read_only_no_orders":True})

    def test_report(self):
        row={key:"待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
        report={"schema":"SKY_DAYTRADE_13COL_RESEARCH_V2","rows":[row],"row_count":1,"universe_count":1,"production_eligible":False,"checked_at_tpe":"2026-11-09T13:30:00+08:00"}
        self.assertEqual(len(validate_report(report)),1)
        status=make_status("chat-20261109-a", report)
        self.assertFalse(status["production_eligible"])
        self.assertEqual(status["row_count"],1)

    def test_market_coverage_status(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "rows": [row], "row_count": 1, "universe_count": 1,
                  "production_eligible": False}
        observation = {"observed_price_count": 1, "fresh_executed_count": 0,
                       "by_exchange": {"TWSE": {"universe": 1, "observed_price": 1, "snapshot_rows": 1},
                                       "TPEx": {"universe": 0, "snapshot_rows": 1}},
                       "snapshot_errors": {}}
        result = make_status("chat-20261109-a", report, observation=observation)
        self.assertEqual(result["observed_price_count"], 1)
        self.assertEqual(result["fresh_executed_count"], 0)
        self.assertEqual(result["status"], "REPORT_READY_RESEARCH_ONLY")
        self.assertEqual(result["observed_price_coverage_pct"], 100)
        self.assertEqual(result["quote_execution_sample_size"], 0)
        self.assertIsNone(result["quote_execution_certification_pct"])
        self.assertFalse(result["quote_certification_is_full_market"])

        sampled = make_status("chat-20261109-b", report, observation=observation,
                              stage2={"attempted_count": 4, "verified_executed_count": 3})
        self.assertEqual(sampled["quote_execution_certification_pct"], 75.0)
        self.assertEqual(sampled["quote_execution_sample_size"], 4)
        self.assertFalse(sampled["quote_certification_is_full_market"])

    def test_snapshot_integrity_readback_does_not_certify_trades(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待",
                    "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "rows": [row], "row_count": 1, "universe_count": 1,
                  "production_eligible": False}
        detail = {"TWSE": {"duplicate_symbol_rows": 1,
                            "official_symbol_coverage_pct": 100.0}}
        observation = {"observed_price_count": 1, "fresh_executed_count": 0,
                       "snapshot_integrity": detail,
                       "by_exchange": {"TWSE": {"snapshot_rows": 1},
                                       "TPEx": {"snapshot_rows": 1}}}
        result = make_status("chat-20261110-diagnostic", report,
                             observation=observation)
        self.assertEqual(result["snapshot_integrity"], detail)
        self.assertFalse(result["snapshot_reference_coverage_is_trade_coverage"])
        self.assertFalse(result["stage2_quote_sample_is_whole_market_certification"])
        self.assertFalse(result["production_eligible"])

    def test_zero_observed_never_claims_paid_success(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "rows": [row], "row_count": 1, "universe_count": 1,
                  "production_eligible": False}
        result = make_status("chat-20261109-a", report,
                             observation={"observed_price_count": 0,
                                          "by_exchange": {
                                              "TWSE": {"snapshot_rows": 1},
                                              "TPEx": {"snapshot_rows": 1}}})
        self.assertEqual(result["status"], "DATA_BLOCKED_NO_OBSERVATIONS")
        self.assertIsNone(result["source"])


    def test_duplicate_symbol_blocked(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "rows": [row, dict(row)], "row_count": 2,
                  "universe_count": 2, "production_eligible": False}
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_MISSING_SYMBOL"):
            validate_report(report)

    def test_research_entry_blocked(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "買進", "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "rows": [row], "row_count": 1,
                  "universe_count": 1, "production_eligible": False}
        with self.assertRaisesRegex(ValueError, "RESEARCH_ENTRY_NOT_ALLOWED"):
            validate_report(report)

    def test_preview_prefers_ranked_observation(self):
        rows = []
        for symbol in ("1101", "1102", "1103"):
            row = {key: "待確認" for key in COLUMNS}
            row.update({"股票代碼": symbol, "現在動作": "等待",
                        "正式交易資格": False})
            rows.append(row)
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "rows": rows, "row_count": 3, "universe_count": 3,
                  "production_eligible": False}
        observation = {"observed_price_count": 3, "fresh_executed_count": 0,
                       "ranked_observations": [{"symbol": "1103"},
                                               {"symbol": "1101"}],
                       "by_exchange": {"TWSE": {"snapshot_rows": 3},
                                       "TPEx": {"snapshot_rows": 1}}}
        status = make_status("chat-20261110-a", report, observation=observation)
        self.assertEqual([x["股票代碼"] for x in status["preview"]],
                         ["1103", "1101"])
        self.assertFalse(status["production_eligible"])

    def test_partial_source_failure_is_not_ready(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "rows": [row], "row_count": 1,
                  "universe_count": 1, "production_eligible": False}
        observation = {"observed_price_count": 1, "snapshot_errors": {"OTC": "TimeoutError"},
                       "by_exchange": {"TWSE": {"snapshot_rows": 1},
                                       "TPEx": {"snapshot_rows": 0}}}
        status = make_status("chat-20261110-a", report, observation=observation)
        self.assertEqual(status["status"], "DATA_BLOCKED_SOURCE_FAILURE")
        self.assertEqual(status["block_reason"], "SOURCE_DATA_INCOMPLETE")

    def test_missing_request_fails_closed_and_writes_diagnostic(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import src.sky_chat_bridge as bridge

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(bridge, "REQUEST", root / "missing-request.json"), \
                 patch.object(bridge, "OUTPUT", root / "diagnostics"):
                with self.assertRaises(SystemExit) as err:
                    bridge.main()
                self.assertEqual(err.exception.code, 1)
            status = json.loads((root / "diagnostics" / "latest.json").read_text())
            self.assertEqual(status["status"], "FAILED")
            self.assertFalse(status["production_eligible"])
            self.assertFalse(status["automatic_order"])

    def test_report_missing_column(self):
        report={"schema":"SKY_DAYTRADE_13COL_RESEARCH_V2","rows":[{"股票代碼":"2330"}],"row_count":1,"production_eligible":False}
        with self.assertRaisesRegex(ValueError,"MISSING_13_COLUMNS"):
            validate_report(report)

if __name__=="__main__":
    unittest.main()
