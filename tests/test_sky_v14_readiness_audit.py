"""Safety regression contracts for read-only formal evidence status."""
import unittest

from research.sky_v14_readiness_audit import evidence_check, markdown


def base():
    return {
        "schema": "SKY_CHAT_SCAN_STATUS_V1",
        "scan_id": "123456",
        "request_id": "test-20261110-readonly",
        "data_timestamp": "2026-11-10T11:26:14+08:00",
        "source": "FUGLE_PAID_SNAPSHOT",
        "status": "REPORT_READY_RESEARCH_ONLY",
        "universe_count": 1986,
        "observed_price_count": 1902,
        "fresh_executed_count": 0,
        "stage2_attempted_count": 12,
        "stage2_verified_executed_count": 12,
        "stage2_rate_limited_count": 0,
        "stage2_bounded_operational_probe_pass": True,
        "stage2_quote_preview": [{
            "symbol": "2409", "last_trade_time": "2026-11-10T11:26:20+08:00",
            "executed_trade_verified": True,
            "canonical_v14_p0c_audit": {
                "model_readiness": {"p0_r_risk_inputs_complete": False,
                                    "p0_k_evidence_eligible": False}
            }
        }],
        "v14_ticker_5m_samples": [{
            "symbol": "2409", "candles_timeframe": "5",
            "valid_today_five_min_bars": 30,
            "avg_price_is_certified_vwap": False,
            "breakout_quality_validated": False,
            "complete_execution_cost_rr": False,
            "v14_full_rule_validated": False,
        }],
        "v14_full_rule_validation_complete": False,
        "production_eligible": False, "automatic_order": False,
    }


class FormalReadinessTests(unittest.TestCase):
    def test_realistic_successful_samples_are_never_trades(self):
        report = evidence_check(base())
        self.assertEqual(report["verdict"], "INSUFFICIENT_DATA")
        self.assertFalse(report["a_plus_authorized"])
        self.assertFalse(report["production_eligible"])
        self.assertEqual(report["now_action"], "禁止交易")
        by_gate = {x["gate"]: x for x in report["checks"]}
        self.assertEqual(by_gate["individual_quote_sample"]["status"], "EVIDENCED")
        self.assertEqual(by_gate["five_minute_candle_observed_sample"]["status"], "EVIDENCED")
        for name in ("full_market_fresh_executions", "five_minute_candle_causal_quality", "official_vwap",
                     "breakout_and_anti_chase", "complete_slippage_fill_cost_rr",
                     "p0_r_portfolio_ledger", "p0_k_evidence_ledger",
                     "full_v14_rule_validation"):
            self.assertEqual(by_gate[name]["status"], "NOT_VERIFIED", name)
        self.assertEqual(by_gate["base_cash_cost_profile"]["status"], "EVIDENCED")
        self.assertIn("禁止新進場", markdown(report))

    def test_not_even_all_positive_diagnostic_booleans_can_auto_promote(self):
        x = base()
        x["v14_full_rule_validation_complete"] = True
        x["v14_ticker_5m_samples"][0].update(
            avg_price_is_certified_vwap=True,
            breakout_quality_validated=True,
            complete_execution_cost_rr=True,
            v14_full_rule_validated=True)
        x["stage2_quote_preview"][0]["canonical_v14_p0c_audit"]["model_readiness"] = {
            "p0_r_risk_inputs_complete": True, "p0_k_evidence_eligible": True}
        result = evidence_check(x)
        self.assertFalse(result["a_plus_authorized"])
        self.assertFalse(result["production_eligible"])
        self.assertEqual(result["verdict"], "INSUFFICIENT_DATA")

    def test_missing_metrics_fail_closed(self):
        result = evidence_check({})
        self.assertEqual(result["verdict"], "SOURCE_CONFLICT_BLOCKED")
        self.assertIn("INVALID_OR_MISSING_COUNT_FIELD", result["findings"])
        self.assertFalse(result["a_plus_authorized"])

    def test_inconsistent_full_market_counts_block(self):
        x = base()
        x["observed_price_count"] = 3000
        result = evidence_check(x)
        self.assertEqual(result["verdict"], "SOURCE_CONFLICT_BLOCKED")
        self.assertIn("COUNT_CONTRADICTION", result["findings"])

    def test_bogus_production_promotion_conflicts(self):
        x = base()
        x["production_eligible"] = True
        x["automatic_order"] = True
        result = evidence_check(x)
        self.assertEqual(result["verdict"], "SOURCE_CONFLICT_BLOCKED")
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["automatic_order"])

    def test_rate_limit_is_not_success(self):
        x = base()
        x["stage2_rate_limited_count"] = 1
        result = evidence_check(x)
        check = next(g for g in result["checks"] if g["gate"] == "individual_quote_sample")
        self.assertEqual(check["status"], "NOT_VERIFIED")

    def test_manual_or_invalid_samples_cannot_be_traded(self):
        x = base()
        x["v14_ticker_5m_samples"] = []
        x["stage2_quote_preview"] = []
        result = evidence_check(x)
        check = next(g for g in result["checks"] if g["gate"] == "five_minute_candle_observed_sample")
        self.assertEqual(check["status"], "NOT_VERIFIED")
        self.assertFalse(result["a_plus_authorized"])

    def test_attention_or_incomplete_candles_are_not_causally_certified(self):
        x = base()
        x["v14_ticker_5m_samples"][0].update(
            status="INCOMPLETE_TICKER_OR_5M_EVIDENCE",
            is_attention=True, bar_sequence_valid=True,
            rejected_future_five_min_bars=0,
            excluded_unfinished_five_min_bars=0,
            bar_timestamp_semantics_certified=False,
        )
        d = {item["gate"]: item for item in evidence_check(x)["checks"]}
        self.assertEqual(d["five_minute_candle_observed_sample"]["status"], "EVIDENCED")
        self.assertEqual(d["five_minute_candle_causal_quality"]["status"], "NOT_VERIFIED")

    def test_boolean_bar_count_cannot_pass_observed(self):
        x = base()
        x["v14_ticker_5m_samples"][0]["valid_today_five_min_bars"] = True
        d = {item["gate"]: item for item in evidence_check(x)["checks"]}
        self.assertEqual(d["five_minute_candle_observed_sample"]["status"], "NOT_VERIFIED")
        self.assertEqual(d["five_minute_candle_causal_quality"]["status"], "NOT_VERIFIED")

    def test_audit_never_promotes_even_if_all_candle_evidence_marked_true(self):
        x = base()
        x["v14_ticker_5m_samples"][0].update(
            status="CANDLE_TICKER_RESEARCH_READY_NOT_TRADE",
            bar_sequence_valid=True, rejected_future_five_min_bars=0,
            excluded_unfinished_five_min_bars=0,
            bar_timestamp_semantics_certified=True,
        )
        report = evidence_check(x)
        self.assertFalse(report["production_eligible"])
        self.assertFalse(report["a_plus_authorized"])
        self.assertEqual(report["verdict"], "INSUFFICIENT_DATA")

    def test_bool_count_must_not_be_accepted(self):
        x = base()
        x["universe_count"] = True
        result = evidence_check(x)
        self.assertEqual(result["verdict"], "SOURCE_CONFLICT_BLOCKED")


if __name__ == "__main__":
    unittest.main()
