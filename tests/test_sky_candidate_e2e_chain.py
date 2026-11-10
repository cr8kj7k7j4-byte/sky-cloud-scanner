import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from research.sky_candidate_e2e_chain import build, markdown

TPE = ZoneInfo("Asia/Taipei")


def reports():
    now = datetime(2026, 11, 10, 11, 40, tzinfo=TPE)
    stage1 = {
        "schema": "SKY_STAGE1_FUGLE_SNAPSHOT_CANDIDATES_V1",
        "candidate_count": 1,
        "candidates": [{"symbol": "2409", "exchange": "TWSE", "observed_price": 27.7}],
    }
    stage2 = {
        "schema": "SKY_STAGE2_BOUNDED_QUOTE_EVIDENCE_V1",
        "checked_at_tpe": now.isoformat(),
        "attempted_count": 1,
        "production_eligible": False,
        "results": [{
            "symbol": "2409", "exchange": "TWSE",
            "status": "FRESH_EXECUTED_TRADE", "executed_trade_verified": True,
            "verified_trade_price": 27.7,
            "last_trade_time": "2026-11-10T11:39:10+08:00",
            "microstructure": {"average_price": 28.62, "quality_reasons": ["PROVIDER_VOLUME_UNIT_UNCERTIFIED"]},
        }],
    }
    stage3 = {
        "schema": "SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1",
        "production_eligible": False,
        "samples": [{
            "symbol": "2409", "exchange": "TWSE",
            "candles_timeframe": "5", "valid_today_five_min_bars": 30,
            "bar_sequence_valid": True, "bar_timestamp_semantics_certified": False,
            "avg_price_is_certified_vwap": False,
            "status": "CANDLE_TICKER_RESEARCH_READY_NOT_TRADE",
        }],
    }
    return stage1, stage2, stage3


class CandidateEvidenceChainTests(unittest.TestCase):
    def test_connects_bounded_stages_but_never_trades(self):
        report = build(*reports())
        self.assertEqual(report["stage1_candidate_count"], 1)
        self.assertEqual(report["stage2_quote_verified_count"], 1)
        self.assertEqual(report["stage3_five_minute_observed_count"], 1)
        self.assertEqual(report["stage3_causally_certified_count"], 0)
        self.assertFalse(report["formal_market_coverage_certified"])
        self.assertEqual(report["vwap_certified_count"], 0)
        self.assertFalse(report["production_eligible"])
        row = report["rows"][0]
        self.assertEqual(row["p0_r_status"], "RISK_INPUT_REQUIRED")
        self.assertEqual(row["risk_recommended_shares"], 0)
        self.assertEqual(row["action"], "禁止交易")
        self.assertIn("OFFICIAL_VWAP_PROVENANCE", row["evidence_missing"])
        self.assertIn("禁止新進場", markdown(report))

    def test_unverified_quote_does_not_use_snapshot_as_trade(self):
        x = reports()
        x[1]["results"][0]["status"] = "MISSING_EXECUTED_TRADE_TIME"
        x[1]["results"][0]["executed_trade_verified"] = False
        report = build(*x)
        self.assertEqual(report["stage2_quote_verified_count"], 0)
        self.assertIsNone(report["rows"][0]["verified_trade_price"])
        self.assertFalse(report["rows"][0]["five_minute_observed"])

    def test_duplicate_candidates_are_rejected(self):
        x = reports()
        x[0]["candidates"].append(dict(x[0]["candidates"][0]))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_INVALID_CANDIDATE"):
            build(*x)

    def test_unknown_stage2_symbol_is_rejected(self):
        x = reports()
        x[1]["results"][0]["symbol"] = "2330"
        with self.assertRaisesRegex(ValueError, "QUOTE_NOT_IN_SNAPSHOT"):
            build(*x)

    def test_stage3_only_included_if_stage2_had_same_symbol(self):
        x = reports()
        x[2]["samples"][0]["symbol"] = "2330"
        with self.assertRaisesRegex(ValueError, "STAGE3_NOT_IN_STAGE2"):
            build(*x)

    def test_quote_cannot_have_naive_timestamp(self):
        x = reports()
        x[1]["results"][0]["last_trade_time"] = "2026-11-10T11:39:10"
        report = build(*x)
        self.assertEqual(report["stage2_quote_verified_count"], 0)
        self.assertEqual(report["rows"][0]["action"], "禁止交易")

    def test_positive_indicators_cannot_upgrade_production(self):
        x = reports()
        s = x[2]["samples"][0]
        s["bar_timestamp_semantics_certified"] = True
        s["avg_price_is_certified_vwap"] = True
        report = build(*x)
        self.assertEqual(report["stage3_causally_certified_count"], 1)
        self.assertEqual(report["vwap_certified_count"], 1)
        self.assertFalse(report["production_eligible"])
        self.assertFalse(report["rows"][0]["a_plus"])
        self.assertEqual(report["rows"][0]["p0_r_status"], "RISK_INPUT_REQUIRED")

    def test_research_status_conflict_is_rejected(self):
        x = reports()
        x[2]["production_eligible"] = True
        with self.assertRaisesRegex(ValueError, "RESEARCH_STATUS_CONFLICT"):
            build(*x)

    def test_empty_stage2_without_quotes_stays_no_trade(self):
        x = reports()
        x[1]["results"] = []
        x[2]["samples"] = []
        result = build(*x)
        self.assertEqual(result["stage2_quote_verified_count"], 0)
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["automatic_order"])

    def test_zero_account_or_missing_stop_never_size_order(self):
        result = build(*reports())
        row = result["rows"][0]
        self.assertIn("stop", row["risk_required_inputs"])
        self.assertIn("target", row["risk_required_inputs"])
        self.assertIn("account_equity", row["risk_required_inputs"])
        self.assertEqual(row["risk_recommended_shares"], 0)


if __name__ == "__main__":
    unittest.main()
