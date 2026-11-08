import unittest
from research.sky_meta_filter_forward_preflight import build_forward_preflight, REQUIRED_DECISION_FIELDS
from research.sky_meta_filter_source_gate import STRATEGY, REQUIRED


def registry(status="UNRESOLVED"):
    return {"strategy_id":STRATEGY,
            "rules":[{"rule":name,"status":status} for name in REQUIRED]}


WORKFLOW='''name: Sky Cloud Scanner v0.5 + P0-R
on:
  schedule:
    - cron: "5,15,30,50 1 * * 1-5"
jobs:
  scan:
    steps:
      - name: Run scanner
        env:
          FUGLE_API_KEY: ${{ secrets.FUGLE_API_KEY }}
      - name: Verify operational market coverage
        run: test PASS_FULL_MARKET_LIVE
'''


class MetaForwardPreflightTests(unittest.TestCase):
    def test_live_scanner_is_not_automatically_v14_alpha(self):
        result=build_forward_preflight(registry=registry(),scan_workflow_text=WORKFLOW)
        self.assertEqual(result["scanner_workflow_name"],"Sky Cloud Scanner v0.5 + P0-R")
        self.assertTrue(result["scanner_schedule_declared"])
        self.assertTrue(result["full_market_gate_declared"])
        self.assertEqual(len(result["historical_rule_providers_unresolved"]),10)
        self.assertFalse(result["forward_private_ledger_enabled"])
        self.assertEqual(result["admitted_candidates"],0)

    def test_forged_all_fields_and_rule_registry_never_bypass_w0(self):
        fake={field:"FORGED" for field in REQUIRED_DECISION_FIELDS}
        result=build_forward_preflight(registry=registry("HISTORICAL_SNAPSHOT"),
                                       scan_workflow_text=WORKFLOW,
                                       scan_artifact={"deep":[fake]})
        self.assertEqual(result["missing_decision_fields_in_sample"],[])
        self.assertEqual(result["admitted_candidates"],0)
        self.assertEqual(result["candidate_stream_status"],
                         "BLOCKED_PENDING_W0_P0G_SOURCE_CERTIFICATION")

    def test_partial_shortlist_does_not_pass(self):
        result=build_forward_preflight(registry=registry(),
                                       scan_workflow_text=WORKFLOW,
                                       scan_artifact={"deep":[{"symbol":"1101","rank_score":90}]})
        self.assertIn("decision_id",result["missing_decision_fields_in_sample"])
        self.assertEqual(result["sample_shortlist_rows"],1)
        self.assertEqual(result["admitted_candidates"],0)

    def test_requires_actual_workflow(self):
        with self.assertRaisesRegex(ValueError,"scanner_workflow_required"):
            build_forward_preflight(registry=registry(),scan_workflow_text="")


if __name__=="__main__":
    unittest.main()
