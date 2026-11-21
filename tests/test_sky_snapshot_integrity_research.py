"""Deterministic no-market tests for TWSE/TPEx Fugle snapshot diagnostics."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from research.sky_full_universe_information import (
    RESEARCH_EXCLUDED_TIB_SYMBOLS, build, filter_research_universe,
)

NOW = datetime(2026, 11, 23, 9, 20, tzinfo=ZoneInfo("Asia/Taipei"))
UNIVERSE = [
    {"symbol": "1101", "name": "TWSE A", "exchange": "TWSE"},
    {"symbol": "1102", "name": "TWSE B", "exchange": "TWSE"},
    {"symbol": "8089", "name": "TPEx A", "exchange": "TPEx"},
    {"symbol": "8090", "name": "TPEx B", "exchange": "TPEx"},
]


class SnapshotIntegrityResearchTests(unittest.TestCase):
    def test_provider_duplicates_unknown_blank_and_missing_are_separate(self):
        report = build(UNIVERSE, {
            "TSE": {"date": NOW.date().isoformat(), "data": [
                {"symbol": "1101", "lastPrice": 43, "tradeVolume": 100},
                {"symbol": "1101", "lastPrice": 43, "tradeVolume": 100},
                {"symbol": "9999", "lastPrice": 11},
                {"symbol": "", "lastPrice": 15},
                None]},
            "OTC": {"date": NOW.date().isoformat(), "data": [
                {"symbol": "8089", "tradeVolume": 0},
            ]},
        }, NOW)
        twse = report["snapshot_integrity"]["TWSE"]
        tpex = report["snapshot_integrity"]["TPEx"]
        self.assertEqual(twse["duplicate_symbol_rows"], 1)
        self.assertEqual(twse["unexpected_symbols"], 1)
        self.assertEqual(twse["blank_symbol_rows"], 1)
        self.assertEqual(twse["invalid_row_count"], 1)
        self.assertEqual(twse["official_symbols_missing_from_snapshot"], 1)
        self.assertEqual(twse["missing_official_symbols"][0]["symbol"], "1102")
        self.assertEqual(twse["official_symbol_coverage_pct"], 50.0)
        self.assertTrue(twse["api_response_valid"])
        self.assertEqual(tpex["official_symbols_missing_from_snapshot"], 1)
        self.assertEqual(tpex["official_symbol_coverage_pct"], 50.0)
        self.assertEqual(report["zero_reported_volume_no_price_count"], 1)
        self.assertEqual(report["missing_price_count"], 3)
        self.assertEqual(report["snapshot_api_calls_expected_per_scan"], 2)
        self.assertEqual(report["quote_execution_certified_count"], 0)
        self.assertIsNone(report["quote_execution_certification_pct"])
        self.assertFalse(report["missing_price_official_status_certified"])
        self.assertTrue(report["no_order_or_production_promotion"])
        self.assertEqual(report["fresh_executed_count"], 0)

    def test_invalid_market_payload_remains_missing_and_no_trade(self):
        report = build(UNIVERSE, {
            "TSE": {"date": NOW.date().isoformat(), "data": []},
            "OTC": {"date": NOW.date().isoformat(), "data": "not a list"},
        }, NOW, errors={"OTC": "API_INVALID_RESPONSE"})
        self.assertFalse(report["snapshot_integrity"]["TPEx"]["api_response_valid"])
        self.assertEqual(report["snapshot_integrity"]["TPEx"]["raw_rows"], 0)
        self.assertEqual(report["snapshot_integrity"]["TPEx"]["official_symbols_missing_from_snapshot"], 2)
        self.assertEqual(report["snapshot_errors"]["OTC"], "API_INVALID_RESPONSE")
        self.assertEqual(report["observed_price_count"], 0)
        self.assertEqual(report["fresh_executed_count"], 0)

    def test_tib_31_permanently_excluded_without_new_market_or_paid_call(self):
        innovative = [
            {"symbol": symbol, "name": "excluded", "exchange": "TWSE"}
            for symbol in RESEARCH_EXCLUDED_TIB_SYMBOLS
        ]
        self.assertEqual(len(innovative), 31)
        included, excluded = filter_research_universe(innovative + UNIVERSE)
        self.assertEqual(len(excluded), 31)
        self.assertEqual(included, UNIVERSE)
        report = build(included, {"TSE": {"date": NOW.date().isoformat(), "data": []},
                                  "OTC": {"date": NOW.date().isoformat(), "data": []}}, NOW)
        self.assertEqual(set(report["snapshot_integrity"]), {"TWSE", "TPEx"})
        self.assertEqual(report["snapshot_api_calls_expected_per_scan"], 2)
        self.assertEqual(report["universe_count"], len(UNIVERSE))
        self.assertFalse(RESEARCH_EXCLUDED_TIB_SYMBOLS.intersection(
            x["symbol"] for x in report["all_symbols"]))


if __name__ == "__main__":
    unittest.main()
