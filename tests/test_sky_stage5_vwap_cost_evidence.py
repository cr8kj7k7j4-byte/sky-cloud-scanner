import unittest

from research.sky_stage5_vwap_cost_evidence import (
    review_quote_vwap_evidence, review_cost_evidence, review_independent_trades_vwap
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

    def test_extreme_finite_quote_numbers_never_emit_nonfinite_json(self):
        import json
        for avg, turn, volume in (
            (1e308, 1e308, 1e308),
            (1e-308, 1e308, 1e-308),
            (1e-308, 1e-308, 1e-308),
        ):
            with self.subTest(avg=avg, turn=turn, volume=volume):
                result = review_quote_vwap_evidence({
                    "average_price": avg,
                    "total_trade_value_twd": turn,
                    "total_trade_volume_raw": volume,
                })
                self.assertEqual(result["status"], "TURNOVER_VOLUME_AVERAGE_INCONSISTENT")
                self.assertIsNone(result["turnover_to_volume_avg_implied_scale"])
                self.assertFalse(result["vwap_certified"])
                json.dumps(result, allow_nan=False)

    def test_cached_complete_trade_pages_reconcile_but_do_not_certify_vwap(self):
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        def epoch(hour, minute):
            return int(datetime(2026, 11, 23, hour, minute,
                                tzinfo=ZoneInfo("Asia/Taipei")).timestamp() * 1_000_000)
        payload = {"date": "2026-11-23", "symbol": "2330",
                   "exchange": "TWSE", "type": "EQUITY",
                   "data": [{"price": 20, "size": 1, "serial": 1,
                             "time": epoch(9, 5)},
                            {"price": 30, "size": 3, "serial": 2,
                             "time": epoch(9, 6)}]}
        pages = [{"offset": 0, "limit": 500, "isTrial": False, "payload": payload},
                 {"offset": 500, "limit": 500, "isTrial": False,
                  "payload": {**payload, "data": []}}]
        observed = datetime(2026, 11, 23, 14, 50,
                            tzinfo=ZoneInfo("Asia/Taipei"))
        def evaluate(rows=pages, total=4):
            return review_independent_trades_vwap(
                rows, symbol="2330", exchange="TWSE",
                trade_date="2026-11-23", quote_total_volume=total,
                observed_at=observed)
        result = evaluate()
        self.assertEqual(result["status"], "TRADE_PAGES_RECONCILED_RESEARCH_ONLY")
        self.assertEqual(result["calculated_trade_vwap_research"], 27.5)
        self.assertEqual(result["observed_tick_volume"], 4)
        self.assertTrue(result["complete_page_chain_certified"])
        self.assertFalse(result["vwap_certified"])
        self.assertFalse(result["source_provenance_certified"])
        self.assertFalse(result["quote_cutoff_pit_certified"])
        for rows, total in (
            (pages[:-1], 4),  # missing terminal empty page
            ([pages[0], {**pages[1], "offset": 2}], 4),  # broken page chain
            ([{**pages[0], "isTrial": True}, pages[1]], 4),
            ([{**pages[0], "payload": {**payload, "exchange": "TPEx"}}, pages[1]], 4),
            ([{**pages[0], "payload": {**payload, "data": [
                payload["data"][0], payload["data"][0]]}}, pages[1]], 4),
            (pages, 5),  # total-volume mismatch
        ):
            with self.subTest(total=total, rows=rows):
                denied = evaluate(rows, total)
                self.assertEqual(denied["status"], "HOLD_INCOMPLETE_TRADES_SOURCE")
                self.assertIsNone(denied["calculated_trade_vwap_research"])
                self.assertFalse(denied["vwap_certified"])

    def test_missing_or_naive_asof_never_grants_tick_source(self):
        from datetime import datetime
        for time in (None, datetime(2026, 11, 23, 13, 30)):
            out = review_independent_trades_vwap(
                [], symbol="2330", exchange="TWSE",
                trade_date="2026-11-23", quote_total_volume=1,
                observed_at=time)
            self.assertFalse(out["vwap_certified"])
            self.assertIsNone(out["calculated_trade_vwap_research"])

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
