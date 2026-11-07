import unittest
from datetime import date
from research.mcr_v1_year_audit import months, run

class YearAuditTests(unittest.TestCase):
    def test_month_ranges(self):
        spans=list(months(date(2025,11,10),date(2026,11,6)))
        self.assertEqual(spans[0],(date(2025,11,10),date(2025,11,30)))
        self.assertEqual(spans[-1],(date(2026,11,1),date(2026,11,6)))
        self.assertEqual(len(spans),13)

    def test_no_token_not_profitable(self):
        result=run("")
        self.assertEqual(result["status"],"INSUFFICIENT_DATA")
        self.assertIsNone(result["net_expectancy"])
        self.assertIsNone(result["backtest_trades"])

    def test_entitled_still_not_a_backtest(self):
        def stub(dataset,token,**kw):
            if dataset=="TaiwanStockMarginMaintenance":
                return [{"date":"2026-01-06","stock_id":"2337","margin_maintenance":125,
                         "margin_balance":300}]
            return [{"date":"2026-01-06","stock_id":"2337","deal_price":50,
                     "Time":"09:05:00.000","volume":2,"TickType":1}]
        result=run("fake",stub)
        self.assertEqual(result["status"],"DATA_PARTIAL")
        self.assertEqual(result["candidate_symbol_days"],13)  # repeated monthly stub rows, test does not dedupe
        self.assertIsNone(result["profit_factor"])

if __name__=="__main__":
    unittest.main()
