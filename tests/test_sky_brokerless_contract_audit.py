import unittest
from pathlib import Path

from research.sky_brokerless_contract_audit import inspect_text, scan
from research.sky_candidate_e2e_chain import build
from research.sky_paper_only_acceptance import audit_status
from src.sky_chat_bridge import make_status


class BrokerlessResearchContractTest(unittest.TestCase):
    def test_broker_requirement_for_research_is_flagged(self):
        hits = inspect_text("sample.md", "Research must confirm broker account API before scan.")
        self.assertEqual(hits[0]["class"], "POSSIBLE_RESEARCH_PREREQUISITE")

    def test_future_live_requirement_not_flagged_as_research_blocker(self):
        hits = inspect_text("sample.md", "Future live trading must have an authorized brokerage account.")
        self.assertEqual(hits[0]["class"], "LIVE_ONLY_OR_INFORMATIONAL")

    def test_research_no_broker_phrase_not_flagged(self):
        hits = inspect_text("sample.md", "研究／Paper 不需要券商開戶，交易模擬可執行。")
        self.assertEqual(hits[0]["class"], "LIVE_ONLY_OR_INFORMATIONAL")

    def test_brokerless_paper_audit_keeps_live_disabled(self):
        result = audit_status({})
        self.assertFalse(result["broker_account_required_for_research"])
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["live_order_enabled"])

    def test_brokerless_sky_chat_status(self):
        report = {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                  "universe_count": 0, "row_count": 0, "rows": [],
                  "production_eligible": False}
        result = make_status("test-brokerless-001", report)
        self.assertFalse(result["broker_account_required_for_research"])
        self.assertEqual(result["research_mode"], "BROKERLESS_RESEARCH_AND_PAPER_ONLY")
        self.assertFalse(result["production_eligible"])

    def test_live_broker_requirement_not_in_research_evidence_missing(self):
        stage1 = {"schema": "SKY_STAGE1_FUGLE_SNAPSHOT_CANDIDATES_V1",
                  "candidate_count": 1,
                  "candidates": [{"exchange": "TWSE", "symbol": "2409",
                                  "observed_price": 27.7}]}
        stage2 = {"schema": "SKY_STAGE2_BOUNDED_QUOTE_EVIDENCE_V1",
                  "production_eligible": False,
                  "checked_at_tpe": "2026-11-10T12:00:00+08:00",
                  "attempted_count": 1,
                  "results": [{"exchange": "TWSE", "symbol": "2409",
                               "status": "FRESH_EXECUTED_TRADE",
                               "executed_trade_verified": True,
                               "last_trade_time": "2026-11-10T11:59:00+08:00",
                               "verified_trade_price": 27.7, "microstructure": {}}]}
        stage3 = {"schema": "SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1",
                  "production_eligible": False, "samples": []}
        report = build(stage1, stage2, stage3)
        row = report["rows"][0]
        self.assertFalse(row["broker_account_required_for_research"])
        self.assertNotIn("P0_R_CURRENT_PORTFOLIO_LEDGER", row["evidence_missing"])
        self.assertIn("P0_R_CURRENT_PORTFOLIO_LEDGER", row["live_only_evidence_missing"])
        self.assertEqual(row["p0_r_status_scope"], "FUTURE_LIVE_TRADING_ONLY")
        self.assertEqual(row["p0_r_status"], "RISK_INPUT_REQUIRED")
        self.assertFalse(report["production_eligible"])

    def test_repository_audit_scans_current_sources(self):
        repo = Path(__file__).resolve().parents[1]
        report = scan(repo)
        self.assertGreater(report["tracked_text_files_scanned"], 100)
        self.assertFalse(report["broker_account_required_for_research"])
        self.assertFalse(report["live_trading_enabled"])
        self.assertIsInstance(report["possible_research_requirement_files"], list)


if __name__ == "__main__":
    unittest.main()
