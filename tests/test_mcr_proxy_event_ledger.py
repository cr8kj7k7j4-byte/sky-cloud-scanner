import unittest, tempfile, json
from research.mcr_proxy_event_ledger import build_events,write_immutable
class LedgerTests(unittest.TestCase):
    def sample(self):
        return {"coverage":"TWSE_TPEX_VERIFIED","data_quality":"BOTH_MARKETS_PASSED",
                "margin_data_date":"2026-11-06","total":2,"rows":[
                {"stock_id":"1101","exchange":"TWSE","margin_data_date":"2026-11-06",
                 "trade_eligible":False,"two_session_reduction_pct":6,"margin_balance_current_units":1000},
                {"stock_id":"8088","exchange":"TPEx","margin_data_date":"2026-11-06",
                 "trade_eligible":False,"two_session_reduction_pct":8,"margin_balance_current_units":500}]}
    def test_determinism_and_no_order(self):
        a=build_events(self.sample())
        b=build_events(self.sample())
        self.assertEqual(a,b)
        self.assertEqual(a["total"],2)
        for item in a["events"]:
            self.assertFalse(item["execution_authorized"])
            self.assertIsNone(item["entry"])
            self.assertEqual(item["outcome_status"],"PENDING_FORWARD_PRICE_EVIDENCE")
    def test_immutable_same_day_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            p=write_immutable(self.sample(),d)
            self.assertEqual(p,write_immutable(self.sample(),d))
            changed=self.sample();changed["rows"][0]["two_session_reduction_pct"]=99
            with self.assertRaisesRegex(ValueError,"CONFLICT"):
                write_immutable(changed,d)
    def test_unverified_rejected(self):
        a=self.sample();a["coverage"]="TWSE_ONLY"
        with self.assertRaisesRegex(ValueError,"UNVERIFIED"):
            build_events(a)

if __name__=="__main__":unittest.main()
