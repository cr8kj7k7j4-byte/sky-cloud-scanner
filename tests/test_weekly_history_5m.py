"""Offline contract tests; no Fugle API, orders, or retired ledger."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from research.audit_weekly_history_5m import audit_candles, build_report


def candle(ts, value=10):
    return {"date": ts, "open": value, "high": value + 1,
            "low": value - 1, "close": value, "volume": 100}


class HistoricalWeeklyAuditTests(unittest.TestCase):
    def test_valid_timestamped_history_is_not_pit_or_signal_proof(self):
        report = audit_candles([candle("2026-11-16T09:05:00+08:00"),
                                candle("2026-11-20T13:30:00+08:00")])
        self.assertEqual(report["status"], "STRUCTURE_PASS_NOT_PIT_VERIFIED")
        self.assertEqual(report["daily"]["2026-11-16"], 1)
        self.assertEqual(report["daily"]["2026-11-20"], 1)
        self.assertFalse(report["historical_signal_verified"])

    def test_refuse_missing_timezone_and_future_rows(self):
        self.assertEqual(audit_candles([candle("2026-11-16T09:05:00")])["status"], "INVALID")
        self.assertEqual(audit_candles([candle("2026-11-23T09:05:00+08:00")])["status"], "INVALID")

    def test_refuse_duplicates_and_ohlc_corruption(self):
        a = candle("2026-11-16T09:05:00+08:00")
        self.assertEqual(audit_candles([a, a])["status"], "INVALID")
        b = candle("2026-11-16T09:10:00+08:00")
        b["high"] = 1
        self.assertEqual(audit_candles([b])["status"], "INVALID")

    def test_weekly_checks_reuse_canonical_session_end(self):
        # Main's canonical data-quality check rejects 13:35 as regular 5m.
        bad = audit_candles([candle("2026-11-16T13:35:00+08:00")])
        self.assertEqual(bad["status"], "INVALID")
        self.assertTrue(any("outside_regular_session" in e for e in bad["errors"]))

    def test_weekly_checks_reuse_canonical_order_and_ohlcv(self):
        bad = audit_candles([
            candle("2026-11-16T09:10:00+08:00"),
            candle("2026-11-16T09:05:00+08:00"),
        ])
        self.assertEqual(bad["status"], "INVALID")
        self.assertTrue(any("non_ascending_timestamps" in e for e in bad["errors"]))
        negative = audit_candles([candle("2026-11-16T09:05:00+08:00",
                                         value=-1)])
        self.assertEqual(negative["status"], "INVALID")

    def test_no_file_is_explicitly_insufficient(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"sample": [{"symbol": "2330"}]}))
            report = build_report(root, manifest)
            self.assertEqual(report["status"], "INSUFFICIENT_DATA")
            self.assertFalse(report["contemporaneous_model_signals_verified"])



if __name__ == "__main__":
    unittest.main()
