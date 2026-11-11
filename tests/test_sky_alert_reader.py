import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from research.sky_full_universe_information import build
from research.sky_alert_reader import consume, consume_uploaded_receipt

TZ = ZoneInfo("Asia/Taipei")


class SkyAlertReaderTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 11, 10, 0, tzinfo=TZ)
        universe = [{"symbol": "1234", "name": "研究股", "exchange": "TWSE"}]
        snapshots = {"TSE": {"date": self.now.date().isoformat(), "data": [{
            "symbol": "1234", "lastPrice": 50, "tradeVolume": 1000,
            "lastTrade": {"price": 50, "time": self.now.isoformat()},
        }]}}
        self.report = build(universe, snapshots, self.now)

    def test_current_report_never_authorizes_trade(self):
        result = consume(self.report, now=self.now + timedelta(seconds=30))
        self.assertEqual(result["freshness_status"], "CURRENT_REPORT_OBSERVATION_ONLY")
        self.assertFalse(result["production_eligible"])
        self.assertEqual(result["action"], "禁止交易")

    def test_stale_artifact_fails_closed_but_retains_observation(self):
        result = consume(self.report, now=self.now + timedelta(minutes=6))
        self.assertEqual(result["freshness_status"], "STALE_SOURCE")
        self.assertEqual(result["fresh_executed_count_at_read"], 0)
        self.assertEqual(result["report"]["all_symbols"][0]["last_price"], 50)
        self.assertNotEqual(result["report"]["all_symbols"][0]["data_status"], "FRESH_EXECUTED_TRADE")

    def test_future_and_missing_source_time(self):
        self.assertEqual(consume(self.report, now=self.now - timedelta(minutes=2))["freshness_status"], "FUTURE_SOURCE_TIME")
        self.report.pop("checked_at_tpe")
        self.assertEqual(consume(self.report, now=self.now)["freshness_status"], "MISSING_SOURCE_TIME")

    def test_current_report_old_tick_downgrades_row(self):
        self.report["all_symbols"][0]["last_trade_time"] = (self.now - timedelta(minutes=4)).isoformat()
        result = consume(self.report, now=self.now)
        self.assertEqual(result["fresh_executed_count_at_read"], 0)

    def test_empty_artifact_is_rejected(self):
        self.report["all_symbols"] = []
        with self.assertRaisesRegex(ValueError, "EMPTY_SOURCE_ROWS"):
            consume(self.report, now=self.now)

    def test_small_future_source_offset_is_blocked(self):
        self.report["checked_at_tpe"] = (self.now + timedelta(seconds=10)).isoformat()
        result = consume(self.report, now=self.now)
        self.assertEqual(result["freshness_status"], "FUTURE_SOURCE_TIME")
        self.assertEqual(result["fresh_executed_count_at_read"], 0)

    def test_future_execution_cannot_be_fresh(self):
        self.report["all_symbols"][0]["last_trade_time"] = (self.now + timedelta(seconds=10)).isoformat()
        result = consume(self.report, now=self.now)
        self.assertEqual(result["fresh_executed_count_at_read"], 0)
        self.assertEqual(result["report"]["all_symbols"][0]["data_status"], "STALE_AT_READ")
        self.assertFalse(result["production_eligible"])

    def test_nonfinite_last_price_never_certifies_trade(self):
        for bad in (float("inf"), float("-inf"), float("nan")):
            with self.subTest(bad=repr(bad)):
                self.report["all_symbols"][0]["last_price"] = bad
                result = consume(self.report, now=self.now)
                self.assertEqual(result["fresh_executed_count_at_read"], 0)
                self.assertFalse(result["production_eligible"])

    def test_truncated_universe_is_blocked(self):
        self.report["universe_count"] += 1
        with self.assertRaisesRegex(ValueError, "UNIVERSE_COUNT_MISMATCH"):
            consume(self.report, now=self.now)

    def test_duplicate_symbols_are_blocked(self):
        self.report["all_symbols"].append(dict(self.report["all_symbols"][0]))
        self.report["universe_count"] += 1
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SOURCE_SYMBOLS"):
            consume(self.report, now=self.now)

    def test_exchange_coverage_mismatch_is_blocked(self):
        self.report["by_exchange"]["TWSE"]["universe"] += 1
        with self.assertRaisesRegex(ValueError, "EXCHANGE_COVERAGE_MISMATCH"):
            consume(self.report, now=self.now)

    def test_recent_snapshot_without_verified_execution_is_not_current(self):
        self.report["all_symbols"][0]["data_status"] = "SNAPSHOT_REFERENCE"
        result = consume(self.report, now=self.now + timedelta(seconds=30))
        self.assertEqual(result["freshness_status"], "NO_VERIFIED_EXECUTIONS")
        self.assertEqual(result["fresh_executed_count_at_read"], 0)
        self.assertTrue(result["observation_available"])
        self.assertFalse(result["production_eligible"])
        self.assertEqual(result["action"], "禁止交易")

    def test_downloaded_github_receipt_is_revalidated_at_read_clock(self):
        original = consume(self.report, now=self.now)
        original["provenance"] = {
            "schema": "SKY_ALERT_EXTERNAL_READBACK_PROVENANCE_V1",
            "source_repo": "cr8kj7k7j4-byte/sky-cloud-scanner",
            "source_run_id": "42912345678",
            "source_head_sha": "a" * 40,
            "source_artifact": "sky-scan-42912345678",
            "download_outcome": "success",
            "input_sha256": "b" * 64,
            "production_eligible": False,
        }
        result = consume_uploaded_receipt(
            original, expected_run_id="42912345678",
            expected_head_sha="a" * 40, now=self.now + timedelta(minutes=8),
        )
        self.assertTrue(result["provenance_validated_at_read"])
        self.assertEqual(result["freshness_status"], "STALE_SOURCE")
        self.assertEqual(result["fresh_executed_count_at_read"], 0)
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["external_mobile_command_verified"])

    def test_downloaded_github_receipt_rejects_wrong_run_and_sha(self):
        original = consume(self.report, now=self.now)
        original["provenance"] = {
            "schema": "SKY_ALERT_EXTERNAL_READBACK_PROVENANCE_V1",
            "source_repo": "cr8kj7k7j4-byte/sky-cloud-scanner",
            "source_run_id": "42912345678",
            "source_head_sha": "a" * 40,
            "source_artifact": "sky-scan-42912345678",
            "download_outcome": "success",
            "input_sha256": "b" * 64,
            "production_eligible": False,
        }
        with self.assertRaisesRegex(ValueError, "UPLOADED_RUN_ID_MISMATCH"):
            consume_uploaded_receipt(original, expected_run_id="999",
                                     expected_head_sha="a" * 40, now=self.now)
        with self.assertRaisesRegex(ValueError, "UPLOADED_HEAD_SHA_MISMATCH"):
            consume_uploaded_receipt(original, expected_run_id="42912345678",
                                     expected_head_sha="c" * 40, now=self.now)
        original["provenance"]["download_outcome"] = "failure"
        with self.assertRaisesRegex(ValueError, "UPLOADED_DOWNLOAD_NOT_VERIFIED"):
            consume_uploaded_receipt(original, expected_run_id="42912345678",
                                     expected_head_sha="a" * 40, now=self.now)

    def test_invalid_schema_is_rejected(self):
        with self.assertRaises(ValueError):
            consume({}, now=self.now)


if __name__ == "__main__":
    unittest.main()
