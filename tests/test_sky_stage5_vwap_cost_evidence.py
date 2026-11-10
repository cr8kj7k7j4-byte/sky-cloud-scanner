import unittest

from research.sky_stage5_vwap_cost_evidence import (
    review_quote_vwap_evidence, review_cost_evidence
)
from research.sky_candidate_e2e_chain import build
from tests.test_sky_candidate_e2e_chain import reports


class Stage5VwapCostSourceTests(unittest.TestCase):
    def test_reconciled_quote_is_still_not_certified_vwap(self):
        result = review_quote_vwap_evidence({
            "average_price": 28.5,
            "total_trade_value_twd": 2_850_000_000,
            "total_trade_volume_raw": 100_000,
        })
        self.assertEqual(result["status"], "OBSERVATION_RECONCILED_NOT_VWAP_CERTIFIED")
        self.assertAlmostEqual(result["turnover_to_volume_avg_implied_scale"], 1000.0)
        self.assertFalse(result["vwap_certified"])
        self.assertFalse(result["official_volume_unit_contract_certified"])

    def test_absent_and_invalid_quote_data_block(self):
        for evidence in ({}, {"average_price": 12, "total_trade_value_twd": 2, "total_trade_volume_raw": 0},
                         {"average_price": True, "total_trade_value_twd": 10, "total_trade_volume_raw": 1},
                         {"average_price": float("nan"), "total_trade_value_twd": 10, "total_trade_volume_raw": 1}):
            result = review_quote_vwap_evidence(evidence)
            self.assertEqual(result["status"], "INCOMPLETE_PROVIDER_AVERAGE_OR_TURNOVER")
            self.assertFalse(result["vwap_certified"])

    def test_inconsistent_units_are_not_certified(self):
        result = review_quote_vwap_evidence({
            "average_price": 28.5,
            "total_trade_value_twd": 285_000,
            "total_trade_volume_raw": 10_000,
        })
        self.assertEqual(result["status"], "TURNOVER_VOLUME_AVERAGE_INCONSISTENT")
        self.assertFalse(result["vwap_certified"])

    def test_calibrated_base_fees_not_complete_cost(self):
        result = review_cost_evidence()
        self.assertEqual(result["profile_id"], "USER_CASH_DAYTRADE_20261022")
        self.assertEqual(result["base_round_trip_cost_pct"], 0.2166)
        self.assertIsNone(result["entry_slippage_bps"])
        self.assertIsNone(result["fill_probability"])
        self.assertFalse(result["execution_cost_complete"])
        self.assertFalse(result["after_cost_rr_certified"])

    def test_existing_stage4_exposes_audits_and_still_blocks(self):
        stage1, stage2, stage3 = reports()
        stage2["results"][0]["microstructure"].update({
            "total_trade_volume_raw": 100000,
            "total_trade_value_twd": 2_862_000_000,
        })
        result = build(stage1, stage2, stage3)
        row = result["rows"][0]
        self.assertEqual(row["vwap_source_consistency_audit"]["status"],
                         "OBSERVATION_RECONCILED_NOT_VWAP_CERTIFIED")
        self.assertFalse(row["vwap_source_consistency_audit"]["vwap_certified"])
        self.assertFalse(row["execution_cost_provenance_audit"]["after_cost_rr_certified"])
        self.assertEqual(row["risk_recommended_shares"], 0)
        self.assertFalse(result["production_eligible"])


if __name__ == "__main__":
    unittest.main()
