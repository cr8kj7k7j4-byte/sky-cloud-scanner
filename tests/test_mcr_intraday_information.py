import unittest
from research.mcr_intraday_information import join, markdown

NOW="2026-11-09T11:35:00+08:00"
MCR={"financing_source_date":"2026-11-06","rows":[
    {"stock_id":"1111","stock_name":"A","exchange":"TWSE","two_session_reduction_pct":12.5},
    {"stock_id":"2222","stock_name":"B","exchange":"TPEx","two_session_reduction_pct":8.1},
]}
LIVE={"checked_at_tpe":NOW,"universe_count":1983,"all_symbols":[
    {"symbol":"1111","exchange":"TWSE","last_price":25.1,"volume":200000,
    "data_status":"UNVERIFIED_EXECUTION_TIME","source":"Fugle paid bulk snapshot"},
]}
class TestMcrLiveObservations(unittest.TestCase):
    def test_keep_all_candidates_even_if_unverified(self):
        r=join(MCR,LIVE,NOW)
        self.assertEqual(r["candidate_count"],2)
        self.assertEqual(r["with_observed_price"],1)
        self.assertEqual(r["fresh_executed_count"],0)
        self.assertFalse(r["trade_eligible"])
        self.assertEqual(r["rows"][0]["last_price"],25.1)
        self.assertEqual(r["rows"][0]["data_status"],"UNVERIFIED_EXECUTION_TIME")
        self.assertEqual(r["rows"][1]["data_status"],"MISSING_LIVE_INFORMATION")
        self.assertTrue(all(not x["trade_eligible"] for x in r["rows"]))
        self.assertIn("🔴",markdown(r))
    def test_missing_live_still_keeps_financing_candidates(self):
        r=join(MCR,None,NOW)
        self.assertEqual(r["candidate_count"],2)
        self.assertEqual(r["with_observed_price"],0)
        self.assertIn("LIVE_ALL_MARKET_OBSERVATIONS_UNAVAILABLE",r["data_blockers"])
    def test_only_explicit_fresh_counted(self):
        live={**LIVE,"all_symbols":[{**LIVE["all_symbols"][0],"data_status":"FRESH_EXECUTED_TRADE"}]}
        r=join(MCR,live,NOW)
        self.assertEqual(r["fresh_executed_count"],1)
        self.assertFalse(r["trade_eligible"])
    def test_preserve_independently_gate_accepted_executed_trade(self):
        valid = {"observations":[{"symbol":"1111","exchange":"TWSE",
            "last":26.3,"trade_time":"2026-11-09T11:46:11+08:00",
            "data_state":"ACCEPTED_EXECUTED_TRADE_BY_MARKET_GATE",
            "source":"TWSE MIS"}]}
        report=join(MCR,LIVE,NOW,valid)
        self.assertEqual(report["independent_accepted_executed_count"],1)
        self.assertEqual(report["rows"][0]["accepted_executed_price"],26.3)
        self.assertFalse(report["trade_eligible"])
        self.assertEqual(report["rows"][0]["data_status"],"UNVERIFIED_EXECUTION_TIME")

    def test_reject_unverified_and_invalid_accepted_feed(self):
        bogus={"observations":[{"symbol":"1111","exchange":"TWSE","last":99,
            "data_state":"UNVERIFIED_EXECUTION_TIME"}]}
        report=join(MCR,LIVE,NOW,bogus)
        self.assertEqual(report["independent_accepted_executed_count"],0)
        self.assertIsNone(report["rows"][0]["accepted_executed_price"])

    def test_no_candidate_unavailable_not_valid_zero_result(self):
        r=join(None,LIVE,NOW)
        self.assertEqual(r["candidate_count"],0)
        self.assertIn("MCR_FINANCING_CANDIDATES_UNAVAILABLE",r["data_blockers"])
    def test_markdown_includes_all_rows_and_missing_trade_columns(self):
        rows = [
            {"stock_id":str(1000+i),"stock_name":"研究股","exchange":"TWSE",
             "two_session_reduction_pct":10.0,"last_price":20.0,"volume":1000,
             "data_status":"UNVERIFIED_EXECUTION_TIME"}
            for i in range(35)
        ]
        report = join({"financing_source_date":"2026-11-06","rows":rows},LIVE,NOW)
        text = markdown(report)
        self.assertIn("|1034|",text)
        self.assertIn("最高接受價",text)
        self.assertIn("融資維持率低於130%",text)
        self.assertIn("UNVERIFIED_EXECUTION_TIME",text)
        self.assertEqual(text.count("|研究股|"),35)
        self.assertIn("\\n|1034|",text)

if __name__=="__main__":unittest.main()
