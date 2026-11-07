import unittest
from research.mcr_merged_proxy import merge_feeds

class McrCombineTests(unittest.TestCase):
    def sample(self,market):
        return {"data_quality":"TWSE_PASSED_TPEX_NOT_CHECKED" if market=="TWSE" else "TPEX_PASSED",
            "mode":"RESEARCH_PROXY_ONLY","margin_data_date":"2026-11-06",
            "rows":[{"stock_id":"1101" if market=="TWSE" else "8088",
                "exchange":market,"margin_data_date":"2026-11-06",
                "maintenance_below_130_verified":False,"trade_eligible":False,
                "two_session_reduction_pct":12.5 if market=="TWSE" else 15.5,
                "margin_balance_current_units":150}],"total":1}
    def test_combined_sorted(self):
        d=merge_feeds(self.sample("TWSE"),self.sample("TPEx"))
        self.assertEqual(d["coverage"],"TWSE_TPEX_VERIFIED")
        self.assertEqual(d["total"],2)
        self.assertEqual(d["rows"][0]["stock_id"],"8088")
        self.assertFalse(d["maintenance_below_130_verified"])
    def test_disagreeing_dates(self):
        t=self.sample("TPEx");t["margin_data_date"]="2026-11-05"
        with self.assertRaisesRegex(ValueError,"SESSION_MISMATCH"):
            merge_feeds(self.sample("TWSE"),t)
    def test_market_not_verified(self):
        t=self.sample("TPEx");t["data_quality"]="BLOCKED_EXTERNAL_DATA"
        with self.assertRaisesRegex(ValueError,"NOT_VERIFIED"):
            merge_feeds(self.sample("TWSE"),t)
    def test_duplicate(self):
        t=self.sample("TPEx");t["rows"][0]["stock_id"]="1101"
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            merge_feeds(self.sample("TWSE"),t)

if __name__=="__main__":unittest.main()
