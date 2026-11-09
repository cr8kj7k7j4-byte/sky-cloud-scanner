import unittest
from research.mcr_observation_report import build_report

def fixture():
    return {
        "mode": "RESEARCH_PROXY_ONLY",
        "data_quality": "BOTH_MARKETS_PASSED",
        "coverage": "TWSE_TPEX_VERIFIED",
        "margin_data_date": "2026-11-06",
        "total": 2,
        "rows": [
            {"stock_id":"1111","exchange":"TWSE","margin_data_date":"2026-11-06","trade_eligible":False,"margin_maintenance_pct":None},
            {"stock_id":"2222","exchange":"TPEx","margin_data_date":"2026-11-06","trade_eligible":False,"margin_maintenance_pct":None},
        ],
    }

class TestMcrObservationReport(unittest.TestCase):
    def test_unverified_scan_still_displays_all_rows(self):
        report=build_report(fixture(),"2026-11-09T11:30:00+08:00",{"market_data_gate":"DATA_BLOCKED"})
        self.assertEqual(report["candidate_count"],2)
        self.assertEqual(report["market_counts"],{"TWSE":1,"TPEx":1})
        self.assertFalse(report["trade_eligible"])
        self.assertTrue(all(not r["trade_eligible"] for r in report["rows"]))
        self.assertTrue(all(r["quote_price"] is None for r in report["rows"]))
        self.assertEqual(report["financing_source_date"],"2026-11-06")

    def test_even_verified_market_gate_cannot_fake_price_join(self):
        scan={"operational_full_market_scan":True,
              "market_data_gate":"PASS_FULL_MARKET_LIVE",
              "live_market_evidence":{"valid_whole_market_operational":True}}
        report=build_report(fixture(),"2026-11-09T11:30:00+08:00",scan)
        self.assertTrue(report["scan_live_gate_verified"])
        self.assertEqual(report["quote_join_status"],"NOT_AVAILABLE")
        self.assertTrue(all(r["quote_timestamp"] is None for r in report["rows"]))

    def test_missing_source_reports_blocker_not_false_no_candidate_claim(self):
        report=build_report(None,"2026-11-09T11:30:00+08:00")
        self.assertIn("MCR_SOURCE_MISSING",report["reasons"])
        self.assertEqual(report["candidate_count"],0)
        self.assertFalse(report["trade_eligible"])

    def test_bad_source_cannot_publish_candidate_rows(self):
        source=fixture()
        source["total"]=999
        report=build_report(source,"2026-11-09T11:30:00+08:00")
        self.assertIn("MCR_SOURCE_COVERAGE_OR_SCHEMA_UNVERIFIED",report["reasons"])
        self.assertEqual(report["rows"],[])

    def test_source_date_inconsistency_blocks_entire_feed(self):
        source=fixture()
        source["rows"][0]["margin_data_date"]="2026-11-05"
        report=build_report(source,"2026-11-09T11:30:00+08:00")
        self.assertIn("MCR_ROW_DATE_MISMATCH",report["reasons"])
        self.assertEqual(report["candidate_count"],0)

if __name__=="__main__":
    unittest.main()
