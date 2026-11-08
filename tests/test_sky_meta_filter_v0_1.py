import copy
import unittest
from research.sky_meta_filter_v0_1 import evaluate, validate_observation


def observation(idx=0, *, decision="ACCEPT", score=.7, exit_proxy=50.5):
    return {
        "schema":"sky-meta-filter-observation-v0.1",
        "signal_id":"id-" + str(idx),"symbol":str(1101+idx),
        "source_event_id":"event-"+str(idx),"baseline_model":"Sky Day Trading v1.4 Dynamic Capital Rotation",
        "baseline_eligible":True,"side":"LONG", "model_version":"META_RESEARCH_V0.1",
        "candidate_at":"2026-11-09T09:10:00+08:00",
        "scored_at":"2026-11-09T09:15:00+08:00",
        "entry_at":"2026-11-09T09:20:00+08:00",
        "entry_proxy":50.0,"stop_proxy":49.0,
        "model_score":score,"model_decision":decision,
        "exit_at":"2026-11-09T13:20:00+08:00" if exit_proxy is not None else None,
        "exit_proxy":exit_proxy,
        "counterfactual_evidence_verified":True if exit_proxy is not None else False,
        "production_signal":False,"order_authorized":False,
    }


def ledger(rows, verified=True):
    return {"schema":"sky-meta-filter-ledger-v0.1",
            "historical_replay_provenance_verified":verified,
            "observations":rows}


class MetaFilterTests(unittest.TestCase):
    def test_reject_nonverified_production_replay(self):
        with self.assertRaisesRegex(ValueError, "historical_production_replay"):
            evaluate(ledger([observation()], False))

    def test_no_future_score_after_entry(self):
        item=observation()
        item["scored_at"]="2026-11-09T09:21:00+08:00"
        with self.assertRaisesRegex(ValueError, "post_entry_score"):
            validate_observation(item)

    def test_missing_outcomes_are_counted_not_filled(self):
        report=evaluate(ledger([observation(0),observation(1,exit_proxy=None)]))
        self.assertEqual(report["observations_total"],2)
        self.assertEqual(report["completed_counterfactual"],1)
        self.assertEqual(report["pending"],1)
        self.assertEqual(report["outcome_completeness"],.5)
        self.assertFalse(report["production_eligible"])

    def test_rejected_and_accepted_are_both_evaluated(self):
        r=evaluate(ledger([
            observation(0,decision="ACCEPT",score=.8,exit_proxy=51),
            observation(1,decision="REJECT",score=.1,exit_proxy=49),
            observation(2,decision="ACCEPT",score=.7,exit_proxy=51),
            observation(3,decision="REJECT",score=.2,exit_proxy=49),
            observation(4,decision="ACCEPT",score=.6,exit_proxy=50.5),
        ]))
        self.assertEqual(r["accepted"]["n"],3)
        self.assertEqual(r["rejected"]["n"],2)
        self.assertEqual(r["top_n"]["3"]["selected"]["n"],3)
        self.assertEqual(r["top_n"]["5"]["selected"]["n"],5)
        self.assertEqual(r["top_n"]["3"]["same_day_eligible_baseline"]["n"],5)
        self.assertEqual(r["auc_primary_cost"],1.0)
        self.assertAlmostEqual(r["accepted"]["expectancy_primary_r"],
                               ((1-.225)+(1-.225)+(.5-.225))/3)

    def test_insufficient_eligible_day_no_top_n(self):
        r=evaluate(ledger([observation(0),observation(1)]))
        self.assertIsNone(r["top_n"]["3"]["selected"])
        self.assertEqual(r["top_n"]["3"]["dates"],0)

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError,"duplicate_signal"):
            evaluate(ledger([observation(),observation()]))

    def test_unverified_counterfactual_rejected(self):
        o=observation()
        o["counterfactual_evidence_verified"]=False
        with self.assertRaisesRegex(ValueError,"unverified_counterfactual"):
            evaluate(ledger([o]))

    def test_invalid_score_or_production_claim_rejected(self):
        for changed in ({"model_score":float("nan")},
                        {"model_score":1.1}, {"production_signal":True},
                        {"baseline_eligible":False}):
            o=observation()
            o.update(changed)
            with self.assertRaises(ValueError):
                evaluate(ledger([o]))

    def test_unverified_future_fill_forbidden(self):
        o=observation(exit_proxy=None)
        o["exit_proxy"]=51
        with self.assertRaisesRegex(ValueError,"partial_outcome"):
            validate_observation(o)


if __name__=="__main__":
    unittest.main()
