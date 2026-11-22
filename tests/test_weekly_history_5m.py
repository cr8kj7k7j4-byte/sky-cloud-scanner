"""Offline contract tests; no Fugle API, orders, or retired ledger."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from research.audit_weekly_history_5m import audit_candles, build_report
from research.download_expanded import _request_chunk


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

    def test_no_file_is_explicitly_insufficient(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"sample": [{"symbol": "2330"}]}))
            report = build_report(root, manifest)
            self.assertEqual(report["status"], "INSUFFICIENT_DATA")
            self.assertFalse(report["contemporaneous_model_signals_verified"])

    def test_atomic_claim_failure_prevents_network(self):
        with patch("research.download_expanded.guard_fugle_request",
                   side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")):
            def no_request(*args, **kwargs):
                raise AssertionError("NETWORK_CALLED_AFTER_DENIED_CLAIM")
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID"):
                _request_chunk("2330", date(2026, 11, 16), date(2026, 11, 20),
                               request_get=no_request)

    def test_429_does_not_retry_under_atomic_claim(self):
        class RateLimited:
            status_code = 429
            headers = {}
            def raise_for_status(self):
                raise AssertionError("unexpected")
        calls = []
        def response(*args, **kwargs):
            calls.append(1)
            return RateLimited()
        with patch("research.download_expanded.guard_fugle_request"), \
             patch.dict("os.environ", {"SKY_PAID_ATOMIC_ENFORCE": "1"}), \
             patch("research.download_expanded.headers", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
                _request_chunk("2330", date(2026, 11, 16), date(2026, 11, 20),
                               request_get=response, sleep_fn=lambda _: None)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
