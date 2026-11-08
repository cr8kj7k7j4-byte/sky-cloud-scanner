import unittest
from research.three_candidate_evidence_gate import evaluate

T0 = "2026-11-06T09:00:00+08:00"
T1 = "2026-11-06T10:00:00+08:00"
T2 = "2026-11-06T11:00:00+08:00"


class CandidateEvidenceGateTest(unittest.TestCase):
    def check(self, candidate, rows):
        return evaluate({"candidate": candidate, "observations": rows})

    def test_empty_is_insufficient(self):
        for name in ("REVENUE_MOM_5D", "MCR", "ETF_0050_TREND"):
            self.assertEqual(self.check(name, [])["evidence_status"], "INSUFFICIENT_DATA")

    def test_revenue_rejects_proxy_and_lookahead(self):
        row = dict(symbol="2330", period="2026-10", published_at=T2,
                   observed_at=T0, decision_at=T1, source_url="https://example.org",
                   source_id="record-1", timestamp_kind="STATUTORY_DEADLINE_PROXY")
        result = self.check("REVENUE_MOM_5D", [row])
        reasons = result["results"][0]["reasons"]
        self.assertIn("LOOKAHEAD_PUBLICATION", reasons)
        self.assertIn("UNVERIFIED_PUBLICATION_TIMESTAMP", reasons)

    def test_verified_revenue_evidence_not_trade_permission(self):
        row = dict(symbol="2330", period="2026-10", published_at=T0,
                   observed_at=T1, decision_at=T2, source_url="https://example.org",
                   source_id="record-1", timestamp_kind="ACTUAL_OFFICIAL_FILING")
        result = self.check("REVENUE_MOM_5D", [row])
        self.assertEqual(result["evidence_status"], "EVIDENCE_INPUT_PASS")
        self.assertEqual(result["trading_qualification"], "RESEARCH_ONLY_NOT_PRODUCTION")

    def test_mcr_aggregate_not_symbol_ratio(self):
        row = dict(symbol="1101", decision_at=T2, observed_at=T1,
                   source_url="https://example.org", margin_maintenance_ratio_pct=128,
                   ratio_asof=T0, ratio_scope="MARKET_AGGREGATE",
                   signal_claim="BELOW_130")
        self.assertIn("RATIO_SCOPE_NOT_SYMBOL_VERIFIED",
                      self.check("MCR", [row])["results"][0]["reasons"])

    def test_mcr_ratio_claim_guard(self):
        row = dict(symbol="1101", decision_at=T2, observed_at=T1,
                   source_url="https://example.org", margin_maintenance_ratio_pct=145,
                   ratio_asof=T0, ratio_scope="VERIFIED_SYMBOL_LEVEL",
                   signal_claim="BELOW_130")
        self.assertIn("BELOW_130_CLAIM_FALSE",
                      self.check("MCR", [row])["results"][0]["reasons"])

    def test_etf_unadjusted_and_mismatched_cost_rejected(self):
        row = dict(symbol="0050", decision_at=T2, observed_at=T1,
                   source_url="https://example.org", strategy_total_return_pct=38,
                   benchmark_total_return_pct=46, cost_pct=0.45,
                   adjustment_basis="PRICE_ONLY", evaluation_start="2025-11-01",
                   evaluation_end="2026-11-01", strategy_cost_basis="AFTER_COST",
                   benchmark_cost_basis="GROSS")
        reasons = self.check("ETF_0050_TREND", [row])["results"][0]["reasons"]
        self.assertIn("DIVIDEND_SPLIT_BASIS_UNVERIFIED", reasons)
        self.assertIn("MISMATCHED_COST_BASIS", reasons)


if __name__ == "__main__":
    unittest.main()
