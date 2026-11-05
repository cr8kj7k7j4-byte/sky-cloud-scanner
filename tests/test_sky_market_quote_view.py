import unittest
from datetime import datetime, timezone, timedelta
from src.sky_market_quote_view import collect, parse_symbols

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 6, 9, 30, tzinfo=TPE)
UNIVERSE = [{"symbol":"2330","exchange":"TWSE","name":"A"},
            {"symbol":"6488","exchange":"TPEx","name":"B"}]

def quote(code):
    return {"date":"2026-11-06","lastPrice":90.0,
            "lastTrade":{"time":int(NOW.timestamp()*1_000_000)}}

class QuoteViewerTests(unittest.TestCase):
    def test_validates_input(self):
        self.assertEqual(parse_symbols("2330,6488,2330"), ["2330","6488"])
        with self.assertRaises(ValueError):
            parse_symbols("2330;6488")
        with self.assertRaises(ValueError):
            parse_symbols(",".join(["2330"]*21))

    def test_two_exchanges_fresh_but_not_whole_market(self):
        result=collect(["2330","6488"],now=NOW,universe=UNIVERSE,fetch=quote)
        self.assertEqual(result["fresh_count"],2)
        self.assertFalse(result["is_whole_market_realtime"])
        self.assertFalse(result["execution_authorized"])
        self.assertEqual([x["exchange"] for x in result["quotes"]],["TWSE","TPEx"])

    def test_off_session_stale_does_not_show_price(self):
        result=collect(["2330"],now=NOW+timedelta(minutes=5),universe=UNIVERSE,fetch=quote)
        self.assertEqual(result["fresh_count"],0)
        self.assertIsNone(result["quotes"][0]["price"])
        self.assertEqual(result["quotes"][0]["status"],"STALE_EXECUTED_TRADE")

    def test_plan_restriction_fail_closed(self):
        def denied(_): raise PermissionError()
        result=collect(["2330"],now=NOW,universe=UNIVERSE,fetch=denied)
        self.assertEqual(result["quotes"][0]["status"],"PLAN_RESTRICTED")

    def test_unknown_symbol_never_fabricated(self):
        result=collect(["9999"],now=NOW,universe=UNIVERSE,fetch=quote)
        self.assertEqual(result["quotes"][0]["status"],"NOT_IN_VERIFIED_OFFICIAL_UNIVERSE")
        self.assertIsNone(result["quotes"][0]["price"])

if __name__=="__main__":
    unittest.main()
