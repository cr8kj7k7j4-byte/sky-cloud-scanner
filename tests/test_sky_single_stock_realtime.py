"""Tests for single-stock realtime freshness and failure handling."""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.sky_single_stock_realtime import collect, timestamp_tpe

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 3, 10, 10, tzinfo=TPE)


def epoch_us(dt):
    return int(dt.timestamp() * 1000000)


class SingleStockRealtimeTests(unittest.TestCase):
    def sample(self, minutes=0):
        t = NOW - timedelta(minutes=minutes)
        quote = {"date": "2026-11-03", "lastPrice": 92.2,
                 "lastTrade": {"time": epoch_us(t)}, "total": {"tradeVolume": 1000},
                 "bids": [{"price": 92.1}], "asks": [{"price": 92.2}]}
        ticker = {"canDayTrade": True}
        return quote, ticker

    def test_timestamp_conversion(self):
        self.assertEqual(timestamp_tpe(epoch_us(NOW)), NOW.isoformat())

    def test_current_quote_no_synthetic_levels(self):
        quote, ticker = self.sample()
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "REALTIME_QUOTE_VERIFIED")
        self.assertIsNone(result["max_entry"])
        self.assertIsNone(result["stop"])
        self.assertFalse(result["execution_authorized"])

    def test_close_only_quote_cannot_be_accepted_as_live_trade(self):
        quote, ticker = self.sample()
        quote.pop("lastPrice")
        quote["closePrice"] = 92.2
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "INVALID_OR_MISSING_PRICE")
        self.assertIsNone(result["last_price"])
        self.assertFalse(result["execution_authorized"])

    def test_missing_lasttrade_time_keeps_observation_without_live_certification(self):
        quote, ticker = self.sample()
        quote.pop("lastTrade")
        quote["closeTime"] = epoch_us(NOW)
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "UNVERIFIED_EXECUTION_TIME")
        self.assertEqual(result["observed_price"], 92.2)
        self.assertIsNone(result["last_trade_tpe"])
        self.assertFalse(result["executed_trade_verified"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["live_order_enabled"])

    def test_stale_quote_fail_closed(self):
        quote, ticker = self.sample(minutes=5)
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "STALE_QUOTE")

    def test_no_day_trade(self):
        quote, ticker = self.sample()
        ticker["canDayTrade"] = False
        with patch("src.sky_single_stock_realtime.fugle.get_quote", return_value=quote), patch(
            "src.sky_single_stock_realtime.fugle.get_ticker", return_value=ticker
        ):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "DAY_TRADE_NOT_ELIGIBLE")

    def test_permission_failure(self):
        with patch("src.sky_single_stock_realtime.fugle.get_quote", side_effect=PermissionError()):
            result = collect("1569", NOW)
        self.assertEqual(result["status"], "QUOTE_FETCH_FAILED")


if __name__ == "__main__":
    unittest.main()
