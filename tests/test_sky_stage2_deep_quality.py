import unittest
from src.sky_stage2_deep_quality import review, canonical_read_only

class DeepQualityTests(unittest.TestCase):
    def quote(self):
        return {"lastTrade": {"price": 28.5}, "avgPrice": 28.0,
                "bids":[{"price":28.5, "size":100}],
                "asks":[{"price":28.55, "size":150}],
                "total":{"tradeVolume":6000, "tradeValue":20000000}}

    def test_good_l1_still_requires_volume_unit_certification(self):
        x=review(self.quote(),verified_trade=True,change_pct=2.0)
        self.assertLess(x["spread_pct"],0.8)
        self.assertIn("PROVIDER_VOLUME_UNIT_UNCERTIFIED",x["quality_reasons"])
        self.assertFalse(x["liquidity_certified"])
        self.assertFalse(x["decision_ready"])
        self.assertTrue(x["turnover_gate_pass"])

    def test_low_trade_value_fails_canonical_minimum(self):
        q=self.quote()
        q["total"]["tradeValue"]=100000
        self.assertIn("TURNOVER_BELOW_UNCHANGED_P0C_MIN",review(q,verified_trade=True,change_pct=1)["quality_reasons"])

    def test_wide_spread_and_chase_deny(self):
        q=self.quote()
        q["asks"][0]["price"]=29.5
        x=review(q,verified_trade=True,change_pct=8.0)
        self.assertIn("SPREAD_GT_P0C_0_8_PCT",x["quality_reasons"])
        self.assertIn("RAPID_RISE_REQUIRES_ANTI_CHASE_REVIEW",x["quality_reasons"])

    def test_missing_book_does_not_claim_quality(self):
        self.assertIn("MISSING_VALID_L1_SPREAD",review({"lastTrade":{"price":30}},verified_trade=True)["quality_reasons"])

    def test_canonical_p0c_no_buy_without_risk_and_evidence(self):
        x=canonical_read_only("2409",review(self.quote(),verified_trade=True))
        self.assertEqual(x["action"],"禁止交易")
        self.assertFalse(x["live_execution_allowed"])
        self.assertFalse(x["model_readiness"]["final_full_rule_v14_validation"])

if __name__ == "__main__":
    unittest.main()
