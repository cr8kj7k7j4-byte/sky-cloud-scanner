import unittest

from research.sky_w0_shared_blocker_audit import audit, classify_market, cron_patterns

FORMAL = """name: formal
on:
  workflow_dispatch:
  schedule:
    - cron: "*/5 1 * * 1-5"
    - cron: "*/5 2-4 * * 1-5"
    - cron: "0-30/5 5 * * 1-5"
permissions:
  contents: read
"""
DISPATCH = FORMAL.replace("name: formal", "name: dispatch")
STATUS = {
    "run_url": "https://github.com/example/actions/runs/123",
    "data_timestamp": "2026-11-10T13:20:00+08:00",
    "universe_count": 1986,
    "stage2_verified_executed_count": 12,
    "candidate_chain_vwap_certified": 0,
}
RUNS = [
    {"name": "Sky Cloud Scanner v0.5 + P0-R", "event": "schedule",
     "status": "completed", "conclusion": "failure", "id": 1, "created_at": "2026-11-10T01:00:00Z"},
    {"name": "Sky Paid Full Market Research Dispatcher Every 5 Minutes", "event": "schedule",
     "status": "completed", "conclusion": "success", "id": 2, "created_at": "2026-11-10T01:00:00Z"},
    {"name": "Sky Cloud Scanner v0.5 + P0-R", "event": "workflow_dispatch",
     "status": "completed", "conclusion": "success", "id": 3},
]


class W0SharedBlockerAuditTest(unittest.TestCase):
    def test_formal_and_dispatch_crons_overlap_not_provider_cost_proof(self):
        result = audit(STATUS, workflow_source={"scan.yml": FORMAL,
                       "sky-full-market-five-minute-dispatch.yml": DISPATCH},
                       scheduled_runs=RUNS)
        self.assertEqual(len(cron_patterns(FORMAL)), 3)
        self.assertTrue(result["schedule"]["same_cron_duplicate_dispatch_risk"])
        self.assertFalse(result["schedule"]["actual_duplicate_paid_requests_confirmed"])
        self.assertFalse(result["schedule"]["api_usage_bill_verified"])
        self.assertEqual(result["schedule"]["formal_scan"]["sampled_failed"], 1)
        self.assertEqual(result["schedule"]["paid_research_dispatch"]["sampled_success"], 1)
        self.assertEqual(result["schedule"]["formal_scan"]["sampled_success"], 0)
        self.assertFalse(result["schedule"]["all_55_slots_certified"])

    def test_bounded_quote_sample_does_not_certify_whole_market(self):
        v = classify_market(STATUS)
        self.assertEqual(v["classification"], "BOUNDED_QUOTE_SAMPLE_ONLY")
        self.assertEqual(v["verified_quote_count"], 12)
        self.assertTrue(v["research_observation_available"])
        self.assertFalse(v["whole_market_execution_certified"])

    def test_unknown_broker_account_is_not_research_blocker(self):
        report = audit(STATUS)
        self.assertFalse(report["broker_account_required_for_research"])
        self.assertEqual(report["research_access"], "OBSERVATION_ALLOWED_NO_BROKER")
        self.assertFalse(report["production_eligible"])
        self.assertFalse(report["automatic_order"])
        self.assertEqual(report["trade_action"], "禁止交易")

    def test_bad_market_metadata_stays_incomplete(self):
        result = audit({"universe_count": 1986,
                        "stage2_verified_executed_count": 9999})
        self.assertEqual(result["market"]["classification"], "INPUT_INCOMPLETE")
        self.assertFalse(result["market"]["whole_market_execution_certified"])
        self.assertFalse(result["source_market_timestamp_valid"])

    def test_retired_paper_ledger_not_an_acceptance_dependency(self):
        report = audit(STATUS)
        self.assertNotIn("paper_admission", report)
        self.assertNotIn("p0r_paper_admission", report["blockers"])
        self.assertFalse(report["production_eligible"])
        self.assertFalse(report["automatic_order"])

    def test_schedule_event_absence_not_certified(self):
        report = audit(STATUS, workflow_source={
            "scan.yml": FORMAL,
            "sky-full-market-five-minute-dispatch.yml": DISPATCH,
        }, scheduled_runs=[])
        self.assertEqual(report["schedule"]["formal_scan"]["sampled_schedule_events"], 0)
        self.assertFalse(report["schedule"]["all_55_slots_certified"])


if __name__ == "__main__":
    unittest.main()
