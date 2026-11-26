"""Multi-source margin join: offline, fail-closed regression."""
import unittest
from datetime import datetime, timedelta
from src.realtime_quote_evidence import TPE
from src.sky_margin_source_join import join_margin_sources

NOW = datetime(2026, 11, 27, 9, 35, tzinfo=TPE)


def feed():
    quote = {"symbol": "6217", "date": "2026-11-27",
             "lastTrade": {"price": 92.9,
                           "time": int((NOW-timedelta(seconds=10)).timestamp()*1000000),
                           "serial": 123}}
    return {
        "official_universe": [{"symbol":"6217", "exchange":"TWSE"}],
        "universe_total": 1,
        "official_universe_source": "TEST_OFFICIAL_MEMBERSHIP_DECLARATION",
        "ratio_by_symbol":{"6217":{"margin_ratio_pct":"87.8", "ratio_date":"2026-11-26",
                                   "ratio_source":"DISCLOSED_ESTIMATE", "ratio_method":"EXPLICIT_ESTIMATION"}},
        "capital_by_symbol":{"6217":{"paid_in_capital_twd":"1172000000","capital_date":"2026-11-26",
                                     "capital_source":"ISSUER_REPORTED_CAPITAL"}},
        "volume_by_symbol":{"6217":{"previous_volume_lots":"3249","volume_date":"2026-11-26",
                                    "volume_source":"TWSE_DAILY_VOLUME_LOTS"}},
        "fugle_quotes_by_symbol":{"6217":quote},
        "observed_at":NOW, "previous_session_date":"2026-11-26",
    }


class MarginSourceJoinTests(unittest.TestCase):
    def test_full_offline_join_only_observes(self):
        x=join_margin_sources(**feed())
        self.assertEqual(x["screened_count"],1)
        self.assertEqual(x["trade_status"],"NO_TRADE")
        self.assertFalse(x["official_universe_independently_verified"])
        self.assertFalse(x["provider_entitlement_verified"])
        self.assertFalse(x["buy_eligible"])
        self.assertEqual(x["candidates"][0]["symbol"],"6217")

    def test_missing_ratio_is_rejected(self):
        x=feed()
        x["ratio_by_symbol"]={}
        out=join_margin_sources(**x)
        self.assertEqual(out["screened_count"],0)
        self.assertEqual(out["missing_ratio_records"],1)

    def test_missing_capital_or_volume_is_rejected(self):
        for field in ("capital_by_symbol","volume_by_symbol"):
            with self.subTest(field=field):
                x=feed(); x[field]={}
                self.assertEqual(join_margin_sources(**x)["screened_count"],0)

    def test_missing_quote_is_rejected(self):
        x=feed();x["fugle_quotes_by_symbol"]={}
        out=join_margin_sources(**x)
        self.assertEqual(out["screened_count"],0)
        self.assertEqual(out["missing_a2_quote_records"],1)

    def test_complete_declared_universe_required(self):
        x=feed();x["universe_total"]=1987
        out=join_margin_sources(**x)
        self.assertEqual(out["candidates"],[])
        self.assertEqual(out["status"],"HOLD_INCOMPLETE_UNIVERSE")

    def test_extra_symbol_rejected_in_any_feed(self):
        for field in ("ratio_by_symbol","capital_by_symbol","volume_by_symbol","fugle_quotes_by_symbol"):
            with self.subTest(field=field):
                x=feed(); x[field]["2330"]={}
                with self.assertRaisesRegex(ValueError,"EXTRA_"):
                    join_margin_sources(**x)

    def test_duplicate_official_universe_rejected(self):
        x=feed();x["official_universe"].append({"symbol":"6217","exchange":"TWSE"})
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OFFICIAL_SYMBOL"):
            join_margin_sources(**x)

    def test_stale_or_trial_quote_rejected_without_other_data_loss(self):
        for changes in ({"isTrial":True},{"date":"2026-11-26"}):
            with self.subTest(changes=changes):
                x=feed();x["fugle_quotes_by_symbol"]["6217"].update(changes)
                out=join_margin_sources(**x)
                self.assertEqual(out["screened_count"],0)
                self.assertEqual(out["missing_ratio_records"],0)


if __name__=="__main__":
    unittest.main()
