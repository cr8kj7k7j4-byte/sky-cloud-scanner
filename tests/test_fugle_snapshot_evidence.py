"""Fugle snapshot is fresh screening context, not verified executed trades."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.fugle_snapshot_evidence import validate_snapshot_screening_rows

TZ = ZoneInfo("Asia/Taipei")


class SnapshotEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 9, 9, 15, tzinfo=TZ)
        self.universe = [
            {"symbol": "2330", "exchange": "TWSE"},
            {"symbol": "8088", "exchange": "TPEx"},
        ]

    def row(self, symbol, seconds=0):
        timestamp = int((self.now - timedelta(seconds=seconds)).timestamp() * 1000000)
        return {"symbol": symbol, "quote_source": "Fugle bulk snapshot",
                "quote_date": self.now.date().isoformat(), "quote_time": str(timestamp),
                "last": 60.0, "volume": 100}

    def test_fresh_snapshot_screening_does_not_certify_executed_trades(self):
        result = validate_snapshot_screening_rows(
            self.universe, [self.row("2330"), self.row("8088")], now=self.now
        )
        self.assertTrue(result["snapshot_screening_ok"])
        self.assertFalse(result["live_whole_market_certified"])
        self.assertFalse(result["last_execution_verified"])
        self.assertEqual(result["quote_scope"], "WHOLE_MARKET_SNAPSHOT_SCREENING_ONLY")

    def test_stale_snapshot_fails_closed(self):
        result = validate_snapshot_screening_rows(
            self.universe, [self.row("2330", 600), self.row("8088")], now=self.now
        )
        self.assertFalse(result["snapshot_screening_ok"])
        self.assertEqual(result["rejected"]["STALE_OR_MISSING_SNAPSHOT_TIME"], 1)

    def test_one_exchange_missing_fails_closed(self):
        result = validate_snapshot_screening_rows(
            self.universe, [self.row("2330")], now=self.now
        )
        self.assertFalse(result["snapshot_screening_ok"])

    def test_reference_price_cannot_replace_last_price(self):
        row = self.row("2330")
        row["last"] = None
        row["closePrice"] = 60
        result = validate_snapshot_screening_rows(
            self.universe, [row, self.row("8088")], now=self.now
        )
        self.assertFalse(result["snapshot_screening_ok"])

    def test_non_fugle_source_rejected(self):
        row = self.row("2330")
        row["quote_source"] = "TWSE MIS"
        result = validate_snapshot_screening_rows(
            self.universe, [row, self.row("8088")], now=self.now
        )
        self.assertFalse(result["snapshot_screening_ok"])


if __name__ == "__main__":
    unittest.main()
