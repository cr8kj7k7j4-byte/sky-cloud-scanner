"""Deterministic safety and output regressions; not a paid API connectivity test."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from research.sky_fugle_independent_scan import classify, render, scan, COLUMNS

TPE = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 11, 9, 10, 0, tzinfo=TPE)


def tickers(market):
    return {"data": [{"symbol": "2330" if market == "TSE" else "8299",
                      "name": "TEST", "type": "EQUITY"}]}


def quotes(market):
    return {"date": "2026-11-09", "data": [{"symbol": "2330" if market == "TSE" else "8299",
                                           "lastPrice": 50, "tradeVolume": 123,
                                           "closeTime": "2026-11-09T10:00:00+08:00"}]}


class IndependentScanTests(unittest.TestCase):
    def test_both_markets_and_no_synthetic_live_quote(self):
        data = scan(now=NOW, ticker_fetch=tickers, snapshot_fetch=quotes)
        self.assertEqual(data["universe_count"], 2)
        self.assertEqual(data["observed_price_count"], 2)
        self.assertEqual(data["fresh_executed_count"], 0)
        self.assertEqual(data["by_exchange"]["TWSE"]["universe"], 1)
        self.assertEqual(data["by_exchange"]["TPEx"]["universe"], 1)
        md, rows = render(data)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(COLUMNS), 13)
        self.assertIn("未驗證", md)
        self.assertTrue(all(x["正式交易資格"] is False for x in rows))
        self.assertTrue(all(x["資料狀態"] == "UNVERIFIED_EXECUTION_TIME" for x in rows))

    def test_afterhours_cannot_certify_live(self):
        meta = {"symbol": "2330", "name": "TEST", "exchange": "TWSE", "market": "TSE"}
        row = classify(meta, {"lastPrice": 50, "lastTrade": {
            "price": 50, "time": "2026-11-09T13:29:30+08:00"}},
            "2026-11-09", datetime(2026, 11, 9, 13, 31, tzinfo=TPE))
        self.assertEqual(row["data_status"], "OUTSIDE_MARKET_SESSION")

    def test_partial_tickers_must_fail(self):
        with self.assertRaises(RuntimeError):
            scan(now=NOW, ticker_fetch=lambda m: (_ for _ in ()).throw(
                RuntimeError("denied")) if m == "OTC" else tickers(m),
                snapshot_fetch=quotes)

    def test_snapshot_fail_is_reported_not_fabricated(self):
        def failing(market):
            if market == "OTC":
                raise PermissionError("denied")
            return quotes(market)
        data = scan(now=NOW, ticker_fetch=tickers, snapshot_fetch=failing)
        self.assertIn("snapshot_OTC", data["errors"])
        self.assertEqual(data["by_exchange"]["TPEx"]["observed_price"], 0)
        self.assertEqual(len(data["all_symbols"]), 2)


if __name__ == "__main__":
    unittest.main()
