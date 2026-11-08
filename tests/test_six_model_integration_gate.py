import unittest
from scripts.six_model_integration_gate import audit

class IntegrationGateTests(unittest.TestCase):
    def test_missing_evidence_is_never_accepted(self):
        report = audit({})
        self.assertEqual(report["overall"], "INSUFFICIENT_DATA")
        self.assertFalse(report["production_promotion"])
        self.assertEqual(len(report["checks"]), 6)

    def test_three_untrained_research_observations_are_not_six_ai_models(self):
        report = audit({"six_model_inference": {
            "verified": True, "inference_run_id": "123",
            "input_fingerprint": "abc",
            "model_results": [{"model_id": x, "executed": True, "real_inference": False}
                              for x in ("bidirectional_intraday", "next_day", "swing_3_20d")]
        }})
        self.assertIn("REQUIRES_SIX_DISTINCT_MODELS",
                      report["checks"]["six_model_inference"]["reasons"])

    def test_deployment_claim_without_revision_not_accepted(self):
        report = audit({"cloud_run": {"verified": True, "service": "tw-ai-mobile",
                                      "http_verified": True, "deployed_commit": "abc",
                                      "run_id": "123"}})
        self.assertEqual(report["checks"]["cloud_run"]["status"], "PENDING")

    def test_no_trading_without_risk_gate(self):
        report = audit({"risk_decision_loop": {"verified": True,
            "risk_gate_executed": False, "decision_recorded": True,
            "order_sent": True, "run_id": "r1"}})
        self.assertIn("UNAUTHORIZED_ORDER_STATE",
                      report["checks"]["risk_decision_loop"]["reasons"])

if __name__ == "__main__":
    unittest.main()
