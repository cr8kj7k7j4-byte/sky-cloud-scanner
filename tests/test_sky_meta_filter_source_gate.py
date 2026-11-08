import unittest

from research.sky_meta_filter_source_gate import (
    candidate_source_inventory, STRATEGY, REQUIRED,
)


def registry(status="UNRESOLVED"):
    return {"strategy_id": STRATEGY,
            "rules": [{"rule": rule, "status": status} for rule in REQUIRED]}


class SourceReadinessTests(unittest.TestCase):
    def test_unresolved_sources_reject_shortlist_as_trades(self):
        document={"deep":[{"symbol":"2330","baseline_eligible":True,
                           "production_eligible":True,"decision_id":"forged"}]}
        out=candidate_source_inventory(registry(),document)
        self.assertEqual(len(out["rule_providers_unresolved"]),10)
        self.assertEqual(out["observed_shortlist_count"],1)
        self.assertEqual(out["admitted_count"],0)
        self.assertFalse(out["research_meta_scoring_enabled"])
        self.assertFalse(out["private_ledger_write_enabled"])

    def test_even_approved_registry_claim_does_not_certify_forward_source(self):
        out=candidate_source_inventory(registry("HISTORICAL_SNAPSHOT"),
                                       {"deep":[{"symbol":"1101","signal_id":"fake"}]})
        self.assertEqual(out["rule_providers_unresolved"],[])
        self.assertEqual(out["forward_source_status"],
                         "AWAITING_W0_CERTIFIED_DECISION_SOURCE")
        self.assertEqual(out["admitted_candidates"],[])

    def test_wrong_strategy_fails(self):
        with self.assertRaisesRegex(ValueError,"unexpected_strategy"):
            candidate_source_inventory({"strategy_id":"RESEARCH_PROXY"})

    def test_unverifiable_source_is_not_silent_pass(self):
        out=candidate_source_inventory(registry())
        self.assertEqual(out["admitted_count"],0)
        self.assertEqual(out["v14_historical_replay_status"],
                         "BLOCKED_FROZEN_PROVIDERS_MISSING")


if __name__=="__main__":
    unittest.main()
