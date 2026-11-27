"""W0 #363: offline Fugle previous-session same-source arithmetic evidence."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from src.sky_completed_session_reconciliation import (
    reconcile, PASS_TRADE, PASS_VOLUME, PASS_MEAN, HOLD,
)
TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 28, 2, 0, tzinfo=TPE)
DAY = datetime(2026, 11, 27, 13, 30, tzinfo=TPE)


def micros(dt):
    return int(dt.timestamp() * 1_000_000)


def example():
    t = micros(DAY)
    s = micros(datetime(2026, 11, 27, 14, 30, tzinfo=TPE))
    rows = [
        {"price": 18.8, "size": 1, "time": t, "serial": 123456},
        {"price": 19, "size": 2, "time": t, "serial": 123457},
        {"price": 19, "size": 5, "time": s, "serial": 99999999},
    ]
    return {
        "symbol": "3717",
        "quote_raw": {
            "symbol": "3717", "exchange": "TWSE", "date": "2026-11-27",
            "lastTrade": {"price": 19, "time": t, "serial": 123457},
            "total": {"transaction": 2, "tradeVolume": 3},
            "avgPrice": 18.93,
        },
        "historical_5m_research": {
            "symbol": "3717", "status": "PASS_COMPLETED_HISTORICAL_5M_RESEARCH_ONLY",
            "source_date": "2026-11-27", "volume_raw_unit": "lots",
            "raw_volume_lots_sum": 3, "source_run_id": "46045172892",
            "source_json_sha256": "a"*64, "reused_no_new_fugle_http": True,
        },
        "trades_raw_pages": [{"offset": 0, "data": rows},
                             {"offset": 500, "data": []}],
        "execution_authorized": False, "automatic_order": False,
    }


class CompletedSessionReconciliationTests(unittest.TestCase):
    def check(self, a=None):
        return reconcile(example() if a is None else a, observed_at=NOW)

    def test_source_4way_volume_and_mean_still_never_certifies_trade(self):
        v = self.check()
        self.assertEqual(v["last_trade_status"], PASS_TRADE)
        self.assertEqual(v["volume_status"], PASS_VOLUME)
        self.assertEqual(v["weighted_mean_status"], PASS_MEAN)
        self.assertEqual(v["regular_trade_count"], 2)
        self.assertEqual(v["excluded_1430_special_trade_count"], 1)
        self.assertEqual(v["regular_trade_volume_lots"], 3)
        self.assertAlmostEqual(v["trades_weighted_mean_research"], 18.933333333)
        self.assertEqual(v["last_trade_tpe"], "2026-11-27T13:30:00+08:00")
        self.assertFalse(v["execution_authorized"])
        self.assertFalse(v["independent_vwap_certified"])
        self.assertFalse(v["cross_source_volume_certified"])
        self.assertFalse(v["current_session_trade_freshness_certified"])

    def test_missing_terminal_page_does_not_claim_full_volume(self):
        a = example()
        a["trades_raw_pages"].pop()
        v = self.check(a)
        self.assertEqual(v["status"], HOLD)
        self.assertEqual(v["reason"], "HOLD_PAGINATION_TERMINAL_NOT_VERIFIED")

    def test_wrong_session_and_quote_symbol_hold(self):
        for k in ("quote_symbol", "history_date", "today"):
            a = example()
            if k == "quote_symbol": a["quote_raw"]["symbol"] = "2330"
            if k == "history_date": a["historical_5m_research"]["source_date"] = "2026-11-26"
            if k == "today": a["historical_5m_research"]["source_date"] = "2026-11-28"; a["quote_raw"]["date"] = "2026-11-28"
            self.assertEqual(self.check(a)["status"], HOLD)

    def test_duplicate_trade_and_wrong_afterhours_timestamp_hold(self):
        a = example()
        a["trades_raw_pages"][0]["data"][1]["serial"] = 123456
        self.assertEqual(self.check(a)["reason"], "HOLD_DUPLICATED_TRADE")
        b = example()
        b["trades_raw_pages"][0]["data"][2]["time"] = micros(DAY + timedelta(minutes=1))
        self.assertEqual(self.check(b)["reason"], "HOLD_OUT_OF_REGULAR_SESSION_TRADE")

    def test_wrong_quote_last_trade_and_transaction_rejected(self):
        for change in ("serial", "count"):
            a = example()
            if change == "serial": a["quote_raw"]["lastTrade"]["serial"] = 666
            else: a["quote_raw"]["total"]["transaction"] = 3
            self.assertEqual(self.check(a)["reason"], "HOLD_LAST_TRADE_OR_TRANSACTION_IDENTITY_MISMATCH")

    def test_volume_and_mean_out_of_tolerance_hold(self):
        a = example()
        a["quote_raw"]["total"]["tradeVolume"] = 99
        self.assertEqual(self.check(a)["reason"], "HOLD_FUGLE_SAME_SOURCE_VOLUME_MISMATCH")
        b = example()
        b["quote_raw"]["avgPrice"] = 100
        self.assertEqual(self.check(b)["reason"], "HOLD_QUOTE_AVG_PRICE_NOT_RECONCILED")

    def test_absent_verified_history_provenance_holds(self):
        for key in ("source_run_id", "source_json_sha256", "reused_no_new_fugle_http"):
            a = example()
            del a["historical_5m_research"][key]
            self.assertEqual(self.check(a)["status"], HOLD)


if __name__ == "__main__":
    unittest.main()
