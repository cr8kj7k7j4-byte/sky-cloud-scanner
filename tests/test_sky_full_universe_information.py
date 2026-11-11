from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.sky_full_universe_information import build, record, summary

NOW = datetime(2026, 11, 9, 11, 30, tzinfo=ZoneInfo("Asia/Taipei"))
U = [
    {"symbol": "1001", "name": "A", "exchange": "TWSE"},
    {"symbol": "2001", "name": "B", "exchange": "TPEx"},
    {"symbol": "2002", "name": "C", "exchange": "TPEx"},
]


def test_all_symbols_preserved_and_info_visible_despite_trade_block():
    snapshots = {
        "TSE": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "1001", "lastPrice": 43, "previousClose": 40,
             "tradeVolume": 1000, "lastTrade": {"time": NOW.isoformat()}}]},
        "OTC": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "2001", "lastPrice": 23, "previousClose": 22,
             "tradeVolume": 500, "lastUpdated": NOW.isoformat()}]},
    }
    report = build(U, snapshots, NOW)
    assert len(report["all_symbols"]) == 3
    assert report["observed_price_count"] == 2
    assert report["fresh_executed_count"] == 1
    assert report["by_exchange"]["TPEx"]["fresh_executed"] == 0
    assert report["trade_decision"].startswith("🔴")
    assert report["ranked_observations"][0]["symbol"] == "1001"
    assert report["all_symbols"][1]["data_status"] == "UNVERIFIED_EXECUTION_TIME"
    assert report["all_symbols"][2]["data_status"] == "MISSING_QUOTE"
    assert "禁止新進場" in summary(report)


def test_stale_timestamp_disclosed_without_production_promotion():
    meta = U[0]
    row = record(meta, {
        "lastPrice": 99, "previousClose": 98,
        "lastTrade": {"time": (NOW - timedelta(minutes=20)).isoformat()},
    }, NOW.date().isoformat(), NOW)
    assert row["last_price"] == 99
    assert row["data_status"] == "STALE_EXECUTION_TIME"
    assert row["production_eligible"] is False
    assert row["trade_signal"] is False


def test_snapshot_old_date_cannot_be_fresh_even_if_trade_clock_is_recent():
    row = record(U[0], {"lastPrice": 80, "lastTrade": {"time": NOW.isoformat()}},
                 "2026-11-06", NOW)
    assert row["data_status"] == "SNAPSHOT_DATE_NOT_TODAY"


def test_zero_price_or_missing_market_is_not_fabricated():
    row = record(U[1], {"lastPrice": 0, "lastUpdated": NOW.isoformat()},
                 NOW.date().isoformat(), NOW)
    assert row["last_price"] is None
    report = build(U, {}, NOW)
    assert report["observed_price_count"] == 0
    assert len(report["all_symbols"]) == 3
    assert report["ranked_observations"] == []


def test_all_mandatory_columns_exist_in_every_stock():
    from research.sky_full_universe_information import REQUIRED_INFORMATION_COLUMNS
    report = build(U, {}, NOW)
    for row in report["all_symbols"]:
        detail = row["required_fields"]
        assert tuple(detail) == REQUIRED_INFORMATION_COLUMNS
        assert detail["即時價"] is None
        assert detail["最近觀察價（可能延遲）"] is None
        assert detail["買進觸發"] is None
        assert detail["多方評分"] is None
        assert detail["現在動作"] == "禁止交易"
    assert report["missing_field_label"] == "待確認（未有可驗證資料）"


def test_stale_observation_not_promoted_to_live_trade():
    old = NOW - timedelta(minutes=30)
    report = build(U, {"TSE": {"date": NOW.date().isoformat(), "data": [
        {"symbol": "1001", "lastPrice": 37.0, "lastTrade": {"time": old.isoformat()}}
    ]}}, NOW)
    row = report["all_symbols"][0]["required_fields"]
    assert row["最近觀察價（可能延遲）"] == 37.0
    assert row["即時價"] is None
    assert row["目標一"] is None
    assert row["最高接受價"] is None


def test_snapshot_without_lasttrade_time_keeps_reference_and_collection_clock():
    payload = {"TSE": {"date": NOW.date().isoformat(), "data": [
        {"symbol": "1001", "lastPrice": 33.5, "tradeVolume": 250,
         "lastUpdated": NOW.isoformat(), "closeTime": NOW.isoformat()}
    ]}}
    report = build(U, payload, NOW)
    row = report["all_symbols"][0]
    assert row["last_price"] == 33.5
    assert row["data_status"] == "UNVERIFIED_EXECUTION_TIME"
    assert row["last_trade_time"] is None
    assert row["snapshot_observed_at"] == NOW.isoformat()
    assert row["required_fields"]["資料時間"] == NOW.isoformat()
    assert row["required_fields"]["最近觀察價（可能延遲）"] == 33.5
    assert row["required_fields"]["即時價"] is None
    assert report["snapshot_reference_requires_last_trade_time"] is False
    assert report["snapshot_reference_without_trade_time_count"] == 1
    assert report["fresh_executed_count"] == 0
    assert report["snapshot_reference_coverage_denominator"] == 3
    assert report["snapshot_reference_coverage_pct"] == 33.33
    assert report["quote_execution_sample_size"] == 0
    assert report["quote_execution_certified_count"] == 0
    assert report["quote_execution_certification_pct"] is None
    assert report["quote_execution_certification_status"] == "NOT_SAMPLED_IN_SNAPSHOT_STAGE"
    assert report["no_order_or_production_promotion"] is True


def test_snapshot_integrity_distinguishes_missing_duplicates_and_no_trades():
    payload = {
        "TSE": {"date": NOW.date().isoformat(), "time": NOW.isoformat(), "data": [
            {"symbol": "1001", "lastPrice": 40, "tradeVolume": 0},
            {"symbol": "1001", "lastPrice": 40, "tradeVolume": 0},
            {"symbol": "9999", "lastPrice": 8},
        ]},
        "OTC": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "2001", "tradeVolume": 0},
        ]},
    }
    report = build(U, payload, NOW)
    twse = report["snapshot_integrity"]["TWSE"]
    tpex = report["snapshot_integrity"]["TPEx"]
    assert twse["api_response_valid"] is True
    assert twse["duplicate_symbol_rows"] == 1
    assert twse["unexpected_symbols"] == 1
    assert twse["official_symbol_coverage_pct"] == 100.0
    assert twse["missing_official_symbols"] == []
    assert twse["snapshot_time_is_execution_time"] is False
    assert tpex["official_symbols_missing_from_snapshot"] == 1
    assert tpex["missing_official_symbols"] == [{"symbol": "2002", "name": "C", "classification": "NOT_RETURNED_BY_FUGLE_SNAPSHOT", "next_check": "FUGLE_TICKER_PRODUCT_TYPE_AND_LISTING_STATUS"}]
    assert report["all_symbols"][1]["data_status"] == "ZERO_REPORTED_VOLUME_NO_PRICE"
    assert report["all_symbols"][1]["source"] == "Fugle paid bulk snapshot"
    assert report["snapshot_api_calls_expected_per_scan"] == 2
    assert report["fresh_executed_count"] == 0


def test_missing_snapshot_market_does_not_look_like_success():
    report = build(U, {"TSE": {"date": NOW.date().isoformat(), "data": []}}, NOW,
                   errors={"OTC": "HTTP_ERROR"})
    assert report["snapshot_integrity"]["TWSE"]["api_response_valid"] is True
    assert report["snapshot_integrity"]["TWSE"]["official_symbols_missing_from_snapshot"] == 1
    assert report["snapshot_integrity"]["TPEx"]["api_response_valid"] is False
    assert report["snapshot_integrity"]["TPEx"]["official_symbols_missing_from_snapshot"] == 2
    assert report["snapshot_errors"]["OTC"] == "HTTP_ERROR"



def test_missing_price_zero_volume_is_separate_from_provider_miss_and_keeps_protection():
    payload = {
        "TSE": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "1001", "tradeVolume": 0, "lastTrade": {}},
        ]},
        "OTC": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "2001", "tradeVolume": 200},
            {"symbol": "2002", "tradeVolume": 0, "lastPrice": 0},
        ]},
    }
    report = build(U, payload, NOW)
    assert report["missing_price_count"] == 3
    assert report["zero_reported_volume_no_price_count"] == 2
    assert report["observed_price_count"] == 0
    rows = {r["symbol"]: r for r in report["all_symbols"]}
    assert rows["1001"]["data_status"] == "ZERO_REPORTED_VOLUME_NO_PRICE"
    assert rows["2001"]["data_status"] == "MISSING_EXECUTED_PRICE"
    assert rows["2002"]["data_status"] == "ZERO_REPORTED_VOLUME_NO_PRICE"
    assert all(r["last_price"] is None for r in rows.values())
    assert report["snapshot_integrity"]["TWSE"]["official_symbol_coverage_pct"] == 100
    assert report["snapshot_integrity"]["TPEx"]["official_symbol_coverage_pct"] == 100
    assert all(d["official_trading_status"] == "UNVERIFIED"
               for d in report["missing_price_diagnostics"])
    assert report["missing_price_official_status_certified"] is False
    assert report["fresh_executed_count"] == 0
    assert report["trade_decision"].startswith("🔴")
    assert report["no_order_or_production_promotion"] is True


def test_zero_volume_with_valid_observation_is_not_reclassified_as_missing_price():
    row = record(U[0], {"lastPrice": 42, "tradeVolume": 0},
                 NOW.date().isoformat(), NOW)
    assert row["last_price"] == 42
    assert row["data_status"] == "UNVERIFIED_EXECUTION_TIME"




# Actual GitHub Actions unittest discovery (not only pytest-style plain functions).
import unittest


class MissingPriceDiagnosticsContracts(unittest.TestCase):
    # CI invokes unittest, not pytest discovery: execute the no-market regressions.
    def test_zero_volume_missing_price_distinguished(self):
        test_missing_price_zero_volume_is_separate_from_provider_miss_and_keeps_protection()

    def test_zero_volume_with_valid_price_is_not_promoted(self):
        test_zero_volume_with_valid_observation_is_not_reclassified_as_missing_price()


class InnovationBoardSnapshotContracts(unittest.TestCase):
    def setUp(self):
        self.universe = [
            {"symbol": "1234", "name": "普通上市", "exchange": "TWSE"},
            {"symbol": "2237", "name": "華德動能-創", "exchange": "TWSE"},
            {"symbol": "2001", "name": "上櫃", "exchange": "TPEx"},
        ]
        self.tse = {"date": NOW.date().isoformat(), "data": [
            {"symbol": "1234", "lastPrice": 42}]}
        self.otc = {"date": NOW.date().isoformat(), "data": [
            {"symbol": "2001", "lastPrice": 33}]}
        self.tib = {"date": NOW.date().isoformat(), "data": [
            {"symbol": "2237", "lastPrice": 55, "lastUpdated": NOW.isoformat()}]}

    def test_tib_is_separate_and_restores_twse_reference_coverage_without_trade_promotion(self):
        from research.sky_full_universe_information import expected_snapshot_market
        report = build(self.universe,
                       {"TSE": self.tse, "OTC": self.otc, "TIB": self.tib}, NOW)
        self.assertEqual(expected_snapshot_market(self.universe[1]), "TIB")
        twse = report["snapshot_integrity"]["TWSE"]
        self.assertEqual(twse["official_symbols_missing_from_snapshot"], 0)
        self.assertEqual(twse["innovation_board_official_count"], 1)
        self.assertEqual(twse["innovation_board_missing_count"], 0)
        self.assertTrue(twse["innovation_board_api_response_valid"])
        self.assertEqual(report["snapshot_api_calls_expected_per_scan"], 3)
        row = next(r for r in report["all_symbols"] if r["symbol"] == "2237")
        self.assertEqual(row["market"], "TIB")
        self.assertEqual(row["last_price"], 55)
        self.assertEqual(row["data_status"], "UNVERIFIED_EXECUTION_TIME")
        self.assertIsNone(row["required_fields"]["即時價"])
        self.assertFalse(row["production_eligible"])
        self.assertEqual(report["fresh_executed_count"], 0)

    def test_missing_tib_is_partial_source_and_never_fabricated(self):
        report = build(self.universe, {"TSE": self.tse, "OTC": self.otc}, NOW,
                       errors={"TIB": "HTTP_403"})
        self.assertEqual(report["snapshot_status"]["TWSE"], "PARTIAL_TIB_MISSING")
        twse = report["snapshot_integrity"]["TWSE"]
        self.assertFalse(twse["api_response_valid"])
        self.assertFalse(twse["innovation_board_api_response_valid"])
        self.assertEqual(twse["innovation_board_missing_count"], 1)
        self.assertEqual(twse["official_symbols_missing_from_snapshot"], 1)
        self.assertEqual(twse["missing_official_symbols"][0]["symbol"], "2237")
        self.assertEqual(report["snapshot_errors"]["TIB"], "HTTP_403")
        self.assertEqual(report["trade_decision"], "🔴 禁止新進場、未驗證通過")

    def test_innovation_name_served_by_tse_is_not_claimed_missing(self):
        # A suffix-based TIB candidate can be returned in the TSE endpoint.
        # Its real provider source must stay TSE; do not invent TIB coverage.
        tse = {"date": NOW.date().isoformat(), "data": [
            {"symbol": "1234", "lastPrice": 42},
            {"symbol": "2237", "lastPrice": 55},
        ]}
        tib = {"date": NOW.date().isoformat(), "data": []}
        report = build(self.universe, {"TSE": tse, "OTC": self.otc, "TIB": tib}, NOW)
        twse = report["snapshot_integrity"]["TWSE"]
        self.assertEqual(twse["official_symbols_missing_from_snapshot"], 0)
        self.assertEqual(twse["innovation_board_missing_count"], 0)
        self.assertEqual(twse["innovation_board_missing_from_tib_endpoint_count"], 1)
        self.assertEqual(twse["innovation_board_found_in_tse_not_tib"], ["2237"])
        row = next(x for x in report["all_symbols"] if x["symbol"] == "2237")
        self.assertEqual(row["snapshot_market_source"], "TSE")
        self.assertEqual(row["market"], "TSE")
        self.assertEqual(row["data_status"], "UNVERIFIED_EXECUTION_TIME")
        self.assertFalse(row["production_eligible"])

    def test_innovation_board_per_symbol_source_receipt(self):
        from research.sky_full_universe_information import build
        # Existing market fixtures: TSE contains ordinary rows, TIB contains the one innovation listing.
        report = build(self.universe, {"TSE": self.tse, "OTC": self.otc, "TIB": self.tib}, NOW)
        details = report["snapshot_integrity"]["TWSE"]["innovation_board_source_by_symbol"]
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["symbol"], "2237")
        self.assertEqual(details[0]["effective_source"], "TIB")
        self.assertTrue(details[0]["in_tib_snapshot"])
        self.assertFalse(details[0]["in_tse_snapshot"])

    def test_tib_unexpected_symbols_remain_diagnostic_not_entries(self):
        tib = {"date": NOW.date().isoformat(), "data": [
            {"symbol": "2237", "lastPrice": 55},
            {"symbol": "9999", "lastPrice": 100},
        ]}
        report = build(self.universe, {"TSE": self.tse, "OTC": self.otc, "TIB": tib}, NOW)
        self.assertEqual(report["snapshot_integrity"]["TWSE"]["unexpected_symbols"], 1)
        self.assertEqual(len(report["all_symbols"]), len(self.universe))
        self.assertFalse(any(r["symbol"] == "9999" for r in report["all_symbols"]))


class SnapshotAcceptanceWorkflowSafetyContracts(unittest.TestCase):
    def test_receipt_artifact_does_not_advance_acceptance_branch_head(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/sky-snapshot-integrity-research-acceptance.yml")
        source = workflow.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("contents: read", source)
        self.assertIn("if-no-files-found: error", source)
        self.assertIn("output/snapshot_integrity_research/receipt.json", source)
        self.assertIn('os.environ.get("GITHUB_SHA")', source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("gh api --method PUT", source)
        self.assertNotIn("GH_TOKEN:", source)

