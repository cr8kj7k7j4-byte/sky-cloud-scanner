"""W0 #363: no-network Fugle historical 5m fail-closed regression."""
import copy
import unittest
from datetime import datetime, date, time, timedelta, timezone

from src.sky_historical_5m_research import evaluate, PASS, HOLD

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 28, 1, 30, tzinfo=TPE)


def source_payload():
    start = datetime(2026, 11, 27, 9, 0, tzinfo=TPE)
    return {
        "symbol": "3717", "exchange": "TWSE", "timeframe": "5",
        "data": [{
            "date": (start + timedelta(minutes=5 * i)).isoformat(),
            "open": 18.4, "high": 18.7, "low": 18.3, "close": 18.5,
            "volume": 9, "average": 18.47,
        } for i in range(55)],
    }


class Historical5mResearchTests(unittest.TestCase):
    def check(self, value):
        return evaluate("3717", "2026-11-27", value, observed_at=NOW)

    def test_complete_session_is_research_only_never_certifies_trade_or_vwap(self):
        v = self.check(source_payload())
        self.assertEqual(v["status"], PASS)
        self.assertEqual(v["completed_bar_count"], 55)
        self.assertEqual(v["raw_volume_lots_sum"], 495)
        self.assertEqual(v["volume_raw_unit"], "lots")
        self.assertTrue(v["last_completed_bar_start_tpe"].endswith("13:30:00+08:00"))
        self.assertFalse(v["production_eligible"])
        self.assertFalse(v["executed_trade_time_certified"])
        self.assertFalse(v["independent_vwap_certified"])
        self.assertFalse(v["execution_authorized"])
        self.assertEqual(v["trade_action"], "禁止交易")
        self.assertIn("NOT_INDEPENDENT_VWAP", v["average_semantics"])

    def test_wrong_date_market_symbol_timeframe_and_missing_return_hold(self):
        for change in ("symbol", "market", "timeframe", "empty", "missing_close"):
            p = source_payload()
            if change == "symbol": p["symbol"] = "2330"
            if change == "market": p["exchange"] = "N/A"
            if change == "timeframe": p["timeframe"] = "D"
            if change == "empty": p["data"] = []
            if change == "missing_close": del p["data"][2]["close"]
            self.assertEqual(self.check(p)["status"], HOLD, change)

    def test_non_session_and_uncompleted_reject(self):
        self.assertEqual(evaluate("3717", "2026-11-28", source_payload(),
                                  observed_at=NOW)["status"], HOLD)
        self.assertEqual(evaluate("3717", "2026-11-29", source_payload(),
                                  observed_at=NOW)["status"], HOLD)
        self.assertEqual(evaluate("3717", "2026-11-30", source_payload(),
                                  observed_at=NOW)["status"], HOLD)

    def test_gaps_duplicate_invalid_timezone_and_auction_missing_reject(self):
        for change in ("gap", "duplicate", "timezone", "closing", "reordered",
                       "negvol", "boolvol", "nan", "future", "outside"):
            p = source_payload()
            if change == "gap": p["data"].pop(13)
            if change == "duplicate": p["data"][12]["date"] = p["data"][11]["date"]
            if change == "timezone": p["data"][10]["date"] = "2026-11-27T09:50:00Z"
            if change == "closing": p["data"].pop()
            if change == "reordered": p["data"][4], p["data"][5] = p["data"][5], p["data"][4]
            if change == "negvol": p["data"][4]["volume"] = -1
            if change == "boolvol": p["data"][4]["volume"] = True
            if change == "nan": p["data"][4]["average"] = float("nan")
            if change == "future": p["data"][4]["date"] = "2026-11-28T10:00:00+08:00"
            if change == "outside": p["data"][4]["date"] = "2026-11-27T14:00:00+08:00"
            self.assertEqual(self.check(p)["status"], HOLD, change)

    def test_no_price_guess_and_api_404_is_hold_not_empty_success(self):
        self.assertEqual(self.check(None)["status"], HOLD)
        self.assertEqual(self.check({"data": []})["status"], HOLD)
        self.assertEqual(self.check({"error": "404 Resource Not Found"})["status"], HOLD)


    def test_transport_parameters_are_bounded_and_not_networked(self):
        from unittest.mock import patch
        from src import fugle
        with patch("src.fugle._get", return_value={"data": []}) as fetch:
            fugle.get_historical_candles_5m("3717", "2026-11-27")
        fetch.assert_called_once_with(
            "/historical/candles/3717",
            {"from": "2026-11-27", "to": "2026-11-27",
             "timeframe": "5", "sort": "asc",
             "fields": "open,high,low,close,volume,average"})
        with patch("src.fugle._get") as fetch:
            for symbol, day in (("bad", "2026-11-27"), ("3717", "2026-11-28"),
                                ("3717", "2026-11-27&key=evil")):
                with self.assertRaises(ValueError):
                    fugle.get_historical_candles_5m(symbol, day)
            fetch.assert_not_called()

    def test_no_paid_history_before_entitlement_and_one_when_approved(self):
        from datetime import date
        from unittest.mock import patch
        from src.sky_single_stock_source_audit import collect
        source_day = date.today() - timedelta(days=1)
        while source_day.weekday() >= 5:
            source_day -= timedelta(days=1)
        day = source_day.isoformat()
        fake_quote = {"date": day, "lastTrade": {}, "total": {}}
        bars = {"data": []}
        with patch("src.sky_single_stock_source_audit.fugle.get_quote", return_value=fake_quote), \
             patch("src.sky_single_stock_source_audit.fugle.get_candles", return_value=bars), \
             patch("src.sky_single_stock_source_audit.fugle.get_trades", return_value={"data": []}), \
             patch("src.sky_single_stock_source_audit.fugle.get_historical_candles_5m") as hist, \
             patch.dict("os.environ", {"SKY_FUGLE_HISTORICAL_ENTITLEMENT_CONFIRMED": "0"}):
            result = collect("3717")
            self.assertEqual(result["historical_5m_research"]["status"], HOLD)
            hist.assert_not_called()
        # An explicit enable permits only one historical request; malformed
        # or incomplete provider data still remains HOLD and never trades.
        with patch("src.sky_single_stock_source_audit.fugle.get_quote", return_value=fake_quote), \
             patch("src.sky_single_stock_source_audit.fugle.get_candles", return_value=bars), \
             patch("src.sky_single_stock_source_audit.fugle.get_trades", return_value={"data": []}), \
             patch("src.sky_single_stock_source_audit.fugle.get_historical_candles_5m", return_value={"data": []}) as hist, \
             patch.dict("os.environ", {"SKY_FUGLE_HISTORICAL_ENTITLEMENT_CONFIRMED": "1"}):
            result = collect("3717")
            hist.assert_called_once_with("3717", day)
            self.assertEqual(result["historical_5m_research"]["status"], HOLD)
            self.assertFalse(result["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
