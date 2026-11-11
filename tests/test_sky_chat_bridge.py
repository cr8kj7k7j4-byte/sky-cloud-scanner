import unittest
from src.sky_chat_bridge import COLUMNS, make_status, validate_report, validate_request

class ChatScanBridgeTests(unittest.TestCase):
    def test_external_artifact_readback_requires_downloaded_evidence(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        self.assertIn("actions: read", workflow)
        self.assertIn('gh run download "$GITHUB_RUN_ID"', workflow)
        self.assertIn("ARTIFACT_RUN_SHA_MISMATCH", workflow)
        self.assertIn('root / "chat_bridge/latest.json"', workflow)
        self.assertIn('root / "sky_quickscan_information/latest_13col.json"', workflow)
        self.assertIn("ARTIFACT_DUPLICATE_SYMBOLS", workflow)
        self.assertIn("sky-chat-readback-", workflow)
        self.assertIn("steps.readback.outcome == 'success'", workflow)

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
