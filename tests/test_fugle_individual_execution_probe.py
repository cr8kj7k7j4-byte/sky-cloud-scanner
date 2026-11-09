"""Fugle-only bounded individual trade-evidence rail; no trade promotion."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from research.sky_fugle_individual_execution_probe import (
    MAX_SAMPLES, select_symbols, verify_samples
)

TPE = ZoneInfo("Asia/Taipei")


def source():
    ranked = []
    for i in range(20):
        ranked.append({"symbol": str(1000 + i), "exchange": "TWSE" if i % 2 == 0 else "TPEx",
                       "source": "Fugle paid bulk snapshot", "last_price": 30,
                       "data_status": "UNVERIFIED_EXECUTION_TIME"})
    ranked[0]["source"] = "TWSE MIS"  # Free source must NEVER enter paid quote probe.
    return {"checked_at_tpe": "2026-11-09T10:00:00+08:00",
            "ranked_observations": ranked}


class TestFugleIndividualProbe(unittest.TestCase):
    def test_bounded_and_excludes_free(self):
        selected = select_symbols(source())
        self.assertLessEqual(len(selected), MAX_SAMPLES)
        self.assertNotIn(("TWSE", "1000"), selected)
        self.assertTrue(any(ex == "TWSE" for ex, _ in selected))
        self.assertTrue(any(ex == "TPEx" for ex, _ in selected))

    def test_quote_last_trade_verified_when_fresh(self):
        now = datetime(2026, 11, 9, 10, 0, tzinfo=TPE)
        ts = int(now.timestamp() * 1000)
        def fake(symbol):
            return {"symbol": symbol, "market": "TSE" if int(symbol) % 2 == 0 else "OTC",
                    "date": "2026-11-09", "lastTrade": {"price": 30.2, "time": ts}}
        report = verify_samples(source(), now=now, quote_fetch=fake)
        self.assertEqual(report["verified_fresh_executed_count"], report["requested_count"])
        self.assertFalse(report["full_market_executed_certified"])
        self.assertFalse(report["production_eligible"])

    def test_close_time_is_not_last_trade(self):
        now = datetime(2026, 11, 9, 10, 0, tzinfo=TPE)
        def fake(symbol):
            return {"symbol": symbol, "market": "TSE" if int(symbol) % 2 == 0 else "OTC",
                    "date": "2026-11-09", "lastPrice": 30,
                    "closeTime": int(now.timestamp() * 1000)}
        result = verify_samples(source(), now=now, quote_fetch=fake)
        self.assertEqual(result["verified_fresh_executed_count"], 0)
        self.assertTrue(all(x["status"] == "MISSING_LAST_TRADE_EVIDENCE" for x in result["rows"]))

    def test_after_close_never_calls_trade_fresh(self):
        now = datetime(2026, 11, 9, 13, 31, tzinfo=TPE)
        ts = int(datetime(2026, 11, 9, 13, 30, tzinfo=TPE).timestamp() * 1000)
        def fake(symbol):
            return {"symbol": symbol, "market": "TSE" if int(symbol) % 2 == 0 else "OTC",
                    "date": "2026-11-09", "lastTrade": {"price": 30, "time": ts}}
        result = verify_samples(source(), now=now, quote_fetch=fake)
        self.assertEqual(result["verified_fresh_executed_count"], 0)
        self.assertTrue(all(x["status"] == "OUTSIDE_REGULAR_SESSION" for x in result["rows"]))

    def test_wrong_exchange_is_rejected(self):
        now = datetime(2026, 11, 9, 10, 0, tzinfo=TPE)
        def fake(symbol):
            return {"symbol": symbol, "market": "TSE", "date": "2026-11-09"}
        result = verify_samples(source(), now=now, quote_fetch=fake)
        self.assertIn("EXCHANGE_MISMATCH", [x["status"] for x in result["rows"]])
