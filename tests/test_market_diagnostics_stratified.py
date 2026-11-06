import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
from src import diagnose_sources as d

class MarketDiagnosticTests(unittest.TestCase):
    def test_both_exchanges_and_bounded_size(self):
        universe = ([{"symbol": str(1000+i), "exchange": "TWSE"} for i in range(100)] +
                    [{"symbol": str(5000+i), "exchange": "TPEx"} for i in range(100)])
        sample = d.stratified_mis_sample(universe)
        self.assertEqual(len(sample), 120)
        self.assertEqual(sum(x["exchange"] == "TWSE" for x in sample), 60)
        self.assertEqual(sum(x["exchange"] == "TPEx" for x in sample), 60)
        self.assertEqual(len(set(x["symbol"] for x in sample)), 120)
        self.assertNotEqual(sample[-1]["symbol"], universe[119]["symbol"])

    def test_one_exchange_absent_no_fabrication(self):
        rows = [{"symbol": str(1000+i), "exchange": "TWSE"} for i in range(3)]
        self.assertEqual(d.stratified_mis_sample(rows), rows)

    def test_explicit_sample_not_certification(self):
        now = datetime.now(ZoneInfo("Asia/Taipei"))
        universe = [
            {"symbol":"2330", "exchange":"TWSE"},
            {"symbol":"6488", "exchange":"TPEx"},
        ]
        def fake_mis(sample):
            return [], ["MIS_LOW_COVERAGE"]
        with patch.object(d, "load_official_universe", return_value=(universe, {"twse":1,"tpex":1})), \
             patch.object(d, "fetch_mis_quotes", side_effect=fake_mis), \
             patch.object(d, "get_tickers", return_value={"data":[]}), \
             patch.object(d, "get_quote", return_value={}), \
             patch.object(d, "snapshot_quotes", side_effect=PermissionError()):
            with patch("builtins.print") as output:
                d.run()
        import json
        payload = json.loads(output.call_args.args[0])
        m = payload["mis_sample"]
        self.assertEqual(m["requested"],2)
        self.assertEqual(m["verified_current_session_trade_count"],0)
        self.assertEqual(m["by_exchange"]["TWSE"]["universe"],1)
        self.assertEqual(m["by_exchange"]["TPEx"]["universe"],1)
        self.assertTrue(m["no_full_market_certification"])
        self.assertEqual(m["scope"],"STRATIFIED_DIAGNOSTIC_SAMPLE_NOT_WHOLE_MARKET")

if __name__ == "__main__":
    unittest.main()
