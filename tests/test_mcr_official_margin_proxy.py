import unittest
from datetime import date
from research.mcr_official_margin_proxy import parse_twse, build_proxy

def payload(day, before=200, after=150, count=550):
    return {"stat":"OK","date":day,"tables":[{"fields":[
        "股票代號","股票名稱","前日餘額","買進","賣出","現金償還","今日餘額",
        "前日餘額","賣出","買進","現券償還","今日餘額"],
        "data":[[str(1000+i),"股票",str(before),"0","50","0",str(after),
                 "0","0","0","0","0"] for i in range(count)]}]}

class OfficialProxyTests(unittest.TestCase):
    def test_date_and_rows(self):
        rows=parse_twse(payload("20261106"),date(2026,11,6))
        self.assertEqual(len(rows),550)
        self.assertEqual(rows["1000"]["margin_balance_delta_units"],-50)
        self.assertIsNone(rows["1000"]["margin_maintenance_pct"])
    def test_no_session_inference(self):
        x=payload("20261106");x.pop("date")
        with self.assertRaisesRegex(ValueError,"SESSION_DATE"):
            parse_twse(x,date(2026,11,6))
    def test_stale_date(self):
        with self.assertRaisesRegex(ValueError,"SESSION_DATE"):
            parse_twse(payload("20261105"),date(2026,11,6))
    def test_low_coverage(self):
        with self.assertRaisesRegex(ValueError,"COVERAGE"):
            parse_twse(payload("20261106",count=5),date(2026,11,6))
    def test_reduction_not_maintenance(self):
        today=parse_twse(payload("20261106"),date(2026,11,6))
        prior=parse_twse(payload("20261105",after=200),date(2026,11,5))
        result=build_proxy(today,prior,report_time="2026-11-08T06:30:00+08:00")
        self.assertEqual(result["total"],550)
        self.assertFalse(result["maintenance_below_130_verified"])
        self.assertTrue(all(r["net_expectancy_per_trade_pct"] is None and
                            not r["trade_eligible"] for r in result["rows"]))

if __name__ == "__main__":unittest.main()
