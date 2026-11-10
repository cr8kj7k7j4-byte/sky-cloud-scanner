import unittest

from research.sky_stage5_breakout_antichase_evidence import audit
from research.sky_candidate_e2e_chain import build
from tests.test_sky_candidate_e2e_chain import reports


def sample():
    candidate = {"symbol": "2409", "exchange": "TWSE", "change_pct_observed": 2.5}
    quote = {"symbol": "2409", "exchange": "TWSE",
             "executed_trade_verified": True, "status": "FRESH_EXECUTED_TRADE",
             "last_trade_time": "2026-11-10T12:20:00+08:00",
             "verified_trade_price": 27.7,
             "microstructure": {"bid": 27.65, "ask": 27.7, "spread_pct": 0.1807,
                                "total_trade_volume_raw": 150000,
                                "total_trade_value_twd": 4500000000,
                                "volume_unit_verified": True, "liquidity_certified": True}}
    candle = {"status": "CANDLE_TICKER_RESEARCH_READY_NOT_TRADE",
              "bar_timestamp_semantics_certified": True,
              "bar_sequence_valid": True,
              "is_disposition": False, "is_attention": False,
              "is_specific_abnormal": False,
              "feature_preview": {"volume_ratio": 1.5, "relative_strength": 0.7}}
    return candidate, quote, candle


class Stage5BreakoutAntiChaseTests(unittest.TestCase):
    def test_full_synthetic_research_evidence_cannot_become_buy_signal(self):
        result = audit(*sample())
        self.assertEqual(result["reasons"], [
            "OFFICIAL_VWAP_CAUSALITY_NOT_CERTIFIED",
            "CANONICAL_BREAKOUT_PRIOR_COMPLETED_BARS_NOT_VERIFIED",
            "BREAKOUT_TRIGGER_AND_FAILURE_NOT_VERIFIED",
            "AFTER_COST_RR_NOT_VERIFIED",
            "P0_R_AND_P0_K_CURRENT_LEDGER_NOT_VERIFIED",
            "W0_P0_G_FORMAL_VALIDATION_REQUIRED",
        ])
        self.assertFalse(result["breakout_quality_certified"])
        self.assertFalse(result["production_eligible"])
        self.assertIsNone(result["price_entry"])

    def test_unverified_quote_blocks(self):
        c, q, k = sample()
        q["executed_trade_verified"] = False
        q["status"] = "MISSING_EXECUTED_TRADE_TIME"
        self.assertIn("UNVERIFIED_LAST_EXECUTED_TRADE", audit(c, q, k)["reasons"])

    def test_snapshot_price_cannot_override_verified_over_100(self):
        c, q, k = sample()
        q["verified_trade_price"] = 100.5
        self.assertIn("EXECUTED_PRICE_OUTSIDE_USER_DAYTRADE_LIMIT", audit(c, q, k)["reasons"])

    def test_rise_6_is_anti_chase_hold_not_buy(self):
        c, q, k = sample()
        c["change_pct_observed"] = 6
        self.assertIn("RAPID_RISE_DIAGNOSTIC_HOLD", audit(c, q, k)["reasons"])

    def test_incomplete_5m_or_unknown_attention_flag_blocks(self):
        c, q, k = sample()
        k["bar_timestamp_semantics_certified"] = False
        k["is_attention"] = None
        reasons = audit(c, q, k)["reasons"]
        self.assertIn("5M_CAUSAL_AVAILABILITY_NOT_CERTIFIED", reasons)
        self.assertIn("UNVERIFIED_OR_RESTRICTED_SECURITY_FLAG", reasons)

    def test_spread_gate_uses_existing_canonical_0_8(self):
        c, q, k = sample()
        q["microstructure"]["spread_pct"] = 1.1
        self.assertIn("SPREAD_EXCEEDS_CANONICAL_0_8_PCT", audit(c, q, k)["reasons"])

    def test_missing_relative_strength_is_not_fabricated(self):
        c, q, k = sample()
        k["feature_preview"]["relative_strength"] = None
        self.assertIn("MARKET_RELATIVE_STRENGTH_MISSING", audit(c, q, k)["reasons"])

    def test_existing_chain_attaches_breakout_checklist(self):
        a, b, c = reports()
        result = build(a, b, c)
        check = result["rows"][0]["breakout_anti_chase_evidence_audit"]
        self.assertFalse(check["anti_chase_full_rule_certified"])
        self.assertFalse(check["trade_trigger_certified"])
        self.assertIn("OFFICIAL_VWAP_CAUSALITY_NOT_CERTIFIED", check["reasons"])
        self.assertEqual(result["rows"][0]["action"], "禁止交易")
        self.assertFalse(result["production_eligible"])


if __name__ == "__main__":
    unittest.main()
