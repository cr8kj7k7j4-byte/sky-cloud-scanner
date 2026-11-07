"""Dependency-free regression tests for isolated Minerva gate."""
import unittest
from research.minerva.minerva_gate import DecisionEvidence, evaluate

BASE = dict(source_verified=True, timestamp_verified=True, coverage_verified=True,
            contradictory_data=False, short_eligible=None, direction="LONG",
            trigger_confirmed=True, chasing=False, stop_valid=True,
            net_rr=2.0, counterargument_reviewed=True, max_risk_ok=True)

class TestMinervaGate(unittest.TestCase):
    def test_complete_evidence_stays_research_only(self):
        result = evaluate(DecisionEvidence(**BASE))
        self.assertEqual((result.action, result.classification), ("觀察", "A"))

    def test_missing_timestamp_is_blocked(self):
        result = evaluate(DecisionEvidence(**{**BASE, "timestamp_verified": False}))
        self.assertIn("INSUFFICIENT_MARKET_DATA", result.reasons)

    def test_unknown_short_eligibility_is_blocked(self):
        result = evaluate(DecisionEvidence(**{**BASE, "direction": "SHORT"}))
        self.assertIn("SHORT_ELIGIBILITY_UNVERIFIED", result.reasons)

    def test_chase_or_low_rr_is_blocked(self):
        result = evaluate(DecisionEvidence(**{**BASE, "chasing": True, "net_rr": 1.2}))
        self.assertEqual(result.action, "禁止交易")

    def test_missing_counterargument_is_blocked(self):
        result = evaluate(DecisionEvidence(**{**BASE, "counterargument_reviewed": False}))
        self.assertIn("COUNTEREVIDENCE_NOT_REVIEWED", result.reasons)

    def test_unconfirmed_trigger_waits(self):
        result = evaluate(DecisionEvidence(**{**BASE, "trigger_confirmed": False}))
        self.assertEqual(result.action, "等待")

if __name__ == "__main__":
    unittest.main()
