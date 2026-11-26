"""No-network regression tests for Fugle A2 evidence parsing in SKY維持率."""
import unittest
from datetime import datetime, timedelta

from src.realtime_quote_evidence import TPE
from src.sky_margin_a2_quote_bridge import margin_row_with_a2_quote
from src.sky_margin_research_filter import filter_margin_observations

NOW = datetime(2026, 11, 27, 9, 35, tzinfo=TPE)


def quote(**updates):
    raw = {"symbol": "6217", "date": "2026-11-27", "isTrial": False,
           "lastPrice": 92.9,
           "lastTrade": {"price": 92.9, "time": int((NOW-timedelta(seconds=20)).timestamp()*1000000),
                         "serial": 123456}}
    raw.update(updates)
    return raw


def row():
    return {"symbol": "6217", "exchange": "TWSE",
            "margin_ratio_pct": "87.8", "ratio_source": "PUBLISHED_ESTIMATE",
            "ratio_date": "2026-11-26", "ratio_method": "estimate",
            "paid_in_capital_twd": "1172000000",
            "capital_source": "PUBLIC_FILING", "capital_date": "2026-11-26",
            "previous_volume_lots": 3249, "volume_source": "OFFICIAL_DAILY",
            "volume_date": "2026-11-26"}


class MarginA2BridgeTests(unittest.TestCase):
    def test_raw_last_trade_into_four_factor_observation_only(self):
        merged = margin_row_with_a2_quote(row(), quote(), observed_at=NOW)
        self.assertEqual(merged["price_quote_validation"],
                         "A2_FIELDS_CHECKED_CALLER_SOURCE_UNVERIFIED")
        self.assertFalse(merged["a2_origin_independently_verified"])
        result = filter_margin_observations(
            [merged], observation_date="2026-11-27",
            previous_session_date="2026-11-26",
            universe_total=1, universe_source="TEST_ONLY_NOT_OFFICIAL")
        self.assertEqual(result["screened_count"], 1)
        self.assertEqual(result["trade_status"], "NO_TRADE")
        self.assertFalse(result["buy_eligible"])

    def test_last_price_fallback_never_counts(self):
        x = margin_row_with_a2_quote(row(), quote(lastTrade={"time":quote()["lastTrade"]["time"], "serial":3}),
                                     observed_at=NOW)
        self.assertEqual(x["price_evidence"], "UNVERIFIED")

    def test_trial_and_stale_date_rejected(self):
        for q in (quote(isTrial=True), quote(date="2026-11-26")):
            with self.subTest(q=q):
                self.assertEqual(margin_row_with_a2_quote(row(), q, observed_at=NOW)["price_evidence"], "UNVERIFIED")

    def test_stale_and_future_trade_rejected(self):
        for delta in (-300, 40):
            q = quote(lastTrade={"price":92.9, "serial":5,
                                 "time": int((NOW+timedelta(seconds=delta)).timestamp()*1000000)})
            self.assertEqual(margin_row_with_a2_quote(row(), q, observed_at=NOW)["price_evidence"], "UNVERIFIED")

    def test_serial_missing_or_invalid_rejected(self):
        for serial in (None, 0, True, "123"):
            q = quote(lastTrade={"price":92.9,"time":quote()["lastTrade"]["time"],"serial":serial})
            self.assertEqual(margin_row_with_a2_quote(row(),q,observed_at=NOW)["price_evidence"],"UNVERIFIED")

    def test_wrong_symbol_never_inherits_price(self):
        q=quote(symbol="2330")
        self.assertEqual(margin_row_with_a2_quote(row(),q,observed_at=NOW)["price_reject_reason"],
                         "QUOTE_SYMBOL_MISMATCH")

    def test_bad_price_and_absent_time(self):
        for price in (None, False, -1, "NaN"):
            q=quote(lastTrade={"price":price,"time":quote()["lastTrade"]["time"],"serial":1})
            self.assertEqual(margin_row_with_a2_quote(row(),q,observed_at=NOW)["price_evidence"],"UNVERIFIED")
        q=quote(lastTrade={"price":92.9,"serial":1})
        self.assertEqual(margin_row_with_a2_quote(row(),q,observed_at=NOW)["price_evidence"],"UNVERIFIED")

    def test_never_trust_preexisting_assertions(self):
        r=row()
        r.update({"price_evidence":"EXECUTED_TRADE", "last_trade_price_twd":"1",
                  "price_source":"FABRICATED", "price_date":"2026-11-27"})
        out=margin_row_with_a2_quote(r,{},observed_at=NOW)
        self.assertEqual(out["price_evidence"],"UNVERIFIED")
        self.assertNotIn("last_trade_price_twd",out)


if __name__ == "__main__":
    unittest.main()
