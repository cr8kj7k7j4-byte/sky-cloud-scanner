import unittest
from datetime import datetime, timezone

from research.sky_meta_filter_w4_source_audit import audit_w4_source_status


def sample():
    return {
        "generated_at_utc":"2026-11-06T09:36:47+00:00",
        "w4_dashboard":{
            "forward_trade_provenance":{"status":"PRODUCTION_DECISION_PROVENANCE_BLOCKED",
                                        "authoritative_forward_rule_source_verified":False},
            "strategy_evidence_integrity":{"ranking_rows_loaded":100,
                                           "eligible_strategy_records":0}
        }
    }


class W4ProvenanceTests(unittest.TestCase):
    def test_ranking_does_not_become_strategy_candidate(self):
        report=audit_w4_source_status(sample(),
                                     observed_at=datetime(2026,11,9,1,0,tzinfo=timezone.utc))
        self.assertEqual(report["ranking_observations"],100)
        self.assertEqual(report["strategy_eligible_records_reported"],0)
        self.assertGreater(report["age_hours"],24)
        self.assertFalse(report["snapshot_is_current_24h"])
        self.assertEqual(report["research_meta_candidate_admission"],0)
        self.assertFalse(report["forward_scoring_enabled"])

    def test_forged_fresh_approved_claim_still_not_meta_authorization(self):
        row=sample()
        row["generated_at_utc"]="2026-11-09T00:00:00+00:00"
        row["w4_dashboard"]["forward_trade_provenance"]["authoritative_forward_rule_source_verified"]=True
        row["w4_dashboard"]["strategy_evidence_integrity"]["eligible_strategy_records"]=100
        report=audit_w4_source_status(row,
                                     observed_at=datetime(2026,11,9,1,0,tzinfo=timezone.utc))
        self.assertEqual(report["strategy_eligible_records_reported"],100)
        self.assertTrue(report["snapshot_is_current_24h"])
        self.assertEqual(report["research_meta_candidate_admission"],0)

    def test_incomplete_snapshot_fails(self):
        row=sample()
        del row["w4_dashboard"]["forward_trade_provenance"]
        with self.assertRaisesRegex(ValueError,"missing_strategy_provenance"):
            audit_w4_source_status(row,observed_at=datetime.now(timezone.utc))

    def test_future_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError,"future_snapshot"):
            audit_w4_source_status(sample(),
                observed_at=datetime(2026,11,1,tzinfo=timezone.utc))


if __name__=="__main__":
    unittest.main()
