import unittest
from src.sky_chat_bridge import COLUMNS, make_status, validate_report, validate_request

class ChatScanBridgeTests(unittest.TestCase):
    def test_final_receipt_enforces_same_request_and_artifact(self):
        from pathlib import Path
        workflow = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        self.assertIn('receipt.get("schema")=="SKY_CHAT_EXTERNAL_ARTIFACT_READBACK_V1"', workflow)
        self.assertIn('receipt.get("request_id")==expected_request_id', workflow)
        self.assertIn('receipt.get("artifact_id","")).isdecimal()', workflow)
        self.assertIn('receipt.get("row_count")>0', workflow)
        self.assertIn('receipt.get("production_eligible") is False', workflow)
        self.assertIn('receipt.get("automatic_order") is False', workflow)

    def test_failure_receipt_workflow_preserves_request_identity(self):
        from pathlib import Path
        workflow = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        self.assertIn('request_id=validate_request(payload)', workflow)
        self.assertIn('"request_id":request_id,', workflow)
        self.assertIn('"automatic_order":False', workflow)
        self.assertIn('"trade_action":"禁止交易"', workflow)

    def test_manual_scan_request_identity_is_unique_and_read_only(self):
        from pathlib import Path
        workflow = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        self.assertIn("if: github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn('validate_request(payload)', workflow)
        self.assertIn('os.environ["GITHUB_RUN_ID"]', workflow)
        self.assertIn('os.environ["GITHUB_RUN_ATTEMPT"]', workflow)
        self.assertIn('payload["request_id"] = f"manual-sky-{run_id}-{attempt}"', workflow)
        self.assertIn('p.write_text(json.dumps(payload', workflow)
        self.assertLess(workflow.index("Assign a unique request ID"),
                        workflow.index("Reserve shared Fugle paid API slot"))
        self.assertIn("Manual GitHub Actions research-only scan; no orders", workflow)

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

    def test_all_five_aliases_use_existing_read_only_runner(self):
        from src.sky_scan_readback import COMMANDS, canonical_command
        self.assertEqual(len(COMMANDS), 5)
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assertEqual(canonical_command(command), "Sky 快掃")
                self.assertEqual(validate_request({
                    "command": command, "request_id": "chat-five-alias-001",
                    "read_only_no_orders": True,
                }), "chat-five-alias-001")
                with self.assertRaisesRegex(ValueError, "ORDER_POLICY_REQUIRED"):
                    validate_request({
                        "command": command, "request_id": "chat-five-alias-001",
                        "read_only_no_orders": False,
                    })

    def test_malformed_command_values_fail_closed_with_value_error(self):
        # JSON payloads may contain lists/dicts instead of a command string.
        # They must be rejected as unsupported commands, not raise TypeError.
        for command in (None, [], {}, ["Sky 快掃"], {"command": "Sky 快掃"}, 0, True):
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError, "UNSUPPORTED_SKY_COMMAND"):
                    validate_request({"command": command,
                                      "request_id": "research-bad-command-001",
                                      "read_only_no_orders": True})

    def test_duplicate_request_id_is_not_a_trade_authorization(self):
        payload = {"command": "Sky 快掃", "request_id": "research-duplicate-001",
                   "read_only_no_orders": True}
        self.assertEqual(validate_request(payload), payload["request_id"])
        self.assertEqual(validate_request(payload), payload["request_id"])
        payload["read_only_no_orders"] = False
        with self.assertRaisesRegex(ValueError, "ORDER_POLICY_REQUIRED"):
            validate_request(payload)

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
        self.assertNotIn("candidate_chain_p0_r_ledger_verified", status)
        self.assertNotIn("live_only_portfolio_ledger_pending", status)
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

    def test_reference_only_run_does_not_claim_live_strategy_ready(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待",
                    "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "rows": [row], "row_count": 1, "universe_count": 1,
                  "production_eligible": False}
        observation = {"observed_price_count": 1, "fresh_executed_count": 0,
                       "by_exchange": {"TWSE": {"snapshot_rows": 1},
                                       "TPEx": {"snapshot_rows": 1}}}
        status = make_status("research-weekend-001", report, observation=observation)
        self.assertEqual(status["status"], "REPORT_READY_RESEARCH_ONLY")
        self.assertEqual(status["research_operational_status"], "REPORT_READY_RESEARCH_ONLY")
        self.assertEqual(status["live_strategy_status"], "HOLD_INSUFFICIENT_DATA")
        self.assertEqual(status["live_strategy_evidence"]["five_minute_observed_count"], 0)
        self.assertEqual(status["live_strategy_evidence"]["vwap_certified_count"], 0)
        self.assertFalse(status["production_eligible"])
        self.assertFalse(status["automatic_order"])

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

    def test_report_missing_column(self):
        report={"schema":"SKY_DAYTRADE_13COL_RESEARCH_V2","rows":[{"股票代碼":"2330"}],"row_count":1,"production_eligible":False}
        with self.assertRaisesRegex(ValueError,"MISSING_13_COLUMNS"):
            validate_report(report)


    def test_weekend_zero_candidates_explains_zero_paid_candle_calls(self):
        from src.sky_chat_bridge import diagnose_five_minute_path
        diagnostic = diagnose_five_minute_path(
            {"candidate_count": 0, "excluded_reasons": {"NON_TRADING_WEEKEND": 1955}},
            {"attempted_count": 0, "verified_executed_count": 0},
            {"attempted_api_requests": 0, "samples": []})
        self.assertEqual(diagnostic["reason_code"], "NON_TRADING_SESSION")
        self.assertEqual(diagnostic["five_minute_api_requests"], 0)
        self.assertFalse(diagnostic["production_eligible"])

    def test_five_minute_diagnostic_distinguishes_quote_and_provider_failures(self):
        from src.sky_chat_bridge import diagnose_five_minute_path
        stage1 = {"candidate_count": 2}
        self.assertEqual(diagnose_five_minute_path(stage1, {"attempted_count": 0}, {})["reason_code"], "STAGE2_NO_QUOTE_REQUESTS")
        self.assertEqual(diagnose_five_minute_path(stage1, {"attempted_count": 2, "verified_executed_count": 0}, {})["reason_code"], "STAGE2_NO_VERIFIED_EXECUTIONS")
        self.assertEqual(diagnose_five_minute_path(stage1, {"attempted_count": 2, "verified_executed_count": 1}, {"attempted_api_requests": 0})["reason_code"], "NO_STAGE2_CANDIDATES_PASSED_5M_GATES")
        self.assertEqual(diagnose_five_minute_path(stage1, {"attempted_count": 2, "verified_executed_count": 1}, {"attempted_api_requests": 2, "samples": [{"status": "HTTP_ERROR"}]})["reason_code"], "FIVE_MINUTE_PROVIDER_ERROR")

    def test_mobile_notice_reports_reason_without_promoting_trade(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2", "rows": [row],
                  "row_count": 1, "universe_count": 1, "production_eligible": False}
        status = make_status("research-weekend-001", report,
            observation={"observed_price_count": 1,
                         "by_exchange": {"TWSE": {"snapshot_rows": 1}, "TPEx": {"snapshot_rows": 1}}},
            stage1={"candidate_count": 0, "excluded_reasons": {"NON_TRADING_WEEKEND": 1}})
        self.assertIn("NON_TRADING_SESSION", status["mobile_research_notice"])
        self.assertFalse(status["automatic_order"])


    def test_5m_sample_429_without_top_level_flag_is_rate_limited(self):
        from src.sky_chat_bridge import diagnose_five_minute_path
        result = diagnose_five_minute_path(
            {"candidate_count": 1}, {"attempted_count": 1, "verified_executed_count": 1},
            {"attempted_api_requests": 1, "samples": [{"status": "RATE_LIMITED", "http_status": 429}]})
        self.assertEqual(result["reason_code"], "FIVE_MINUTE_RATE_LIMITED")
        self.assertFalse(result["automatic_order"])

    def test_mobile_source_failure_never_says_report_readable(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2", "rows": [row],
                  "row_count": 1, "universe_count": 1, "production_eligible": False}
        result = make_status("research-source-error-001", report,
            observation={"observed_price_count": 1, "snapshot_errors": {"TWSE": "timeout"}})
        self.assertEqual(result["status"], "DATA_BLOCKED_SOURCE_FAILURE")
        self.assertIn("資料不完整", result["mobile_research_notice"])
        self.assertNotIn("報告可讀", result["mobile_research_notice"])

    def test_mobile_5m_observed_not_misreported_unverified(self):
        row = {key: "待確認" for key in COLUMNS}
        row.update({"股票代碼": "1101", "現在動作": "等待", "正式交易資格": False})
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2", "rows": [row],
                  "row_count": 1, "universe_count": 1, "production_eligible": False}
        result = make_status("research-5m-observed-001", report,
            observation={"observed_price_count": 1,
                         "by_exchange": {"TWSE": {"snapshot_rows": 1}, "TPEx": {"snapshot_rows": 1}}},
            stage1={"candidate_count": 1},
            stage2={"attempted_count": 1, "verified_executed_count": 1},
            stage3={"attempted_api_requests": 2, "samples": [{"valid_today_five_min_bars": 3}]})
        self.assertEqual(result["five_minute_diagnostic"]["reason_code"], "FIVE_MINUTE_OBSERVED_RESEARCH_ONLY")
        self.assertIn("已取得研究用五分鐘K棒", result["mobile_research_notice"])
        self.assertIn("禁止交易", result["mobile_research_notice"])
        self.assertFalse(result["production_eligible"])

if __name__=="__main__":
    unittest.main()
