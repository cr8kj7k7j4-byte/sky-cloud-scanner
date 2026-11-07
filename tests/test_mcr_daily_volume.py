import unittest
from datetime import date
from research.mcr_daily_volume import parse_market, enrich_merged, collect_and_enrich

DAY = date(2026, 11, 6)
def twse(n=510, dt="20261106"):
    return [{"Date": dt, "Code": str(1000+i), "TradeVolume": f"{(i+1)*1000:,}"} for i in range(n)]
def tpex(n=350, dt="1151106"):
    return [{"Date": dt, "SecuritiesCompanyCode": str(4000+i),
             "TradingShares": f"{(i+1)*500:,}"} for i in range(n)]
def merged():
    return {"coverage":"TWSE_TPEX_VERIFIED","data_quality":"BOTH_MARKETS_PASSED",
        "margin_data_date":"2026-11-06", "rows":[
            {"stock_id":"1000","exchange":"TWSE","trade_eligible":False},
            {"stock_id":"4000","exchange":"TPEx","trade_eligible":False},
            {"stock_id":"4999","exchange":"TPEx","trade_eligible":False}]}

class VolumeTests(unittest.TestCase):
    def test_official_fields_and_units(self):
        self.assertEqual(parse_market(twse(),"TWSE",DAY)["1000"],1000)
        self.assertEqual(parse_market(tpex(),"TPEx",DAY)["4000"],500)
    def test_date_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "DATE_MISMATCH"):
            parse_market(twse(dt="20261105"),"TWSE",DAY)
    def test_roc_date(self):
        self.assertEqual(len(parse_market(tpex(),"TPEx",DAY)),350)
    def test_missing_not_zero(self):
        result=enrich_merged(merged(), {"TWSE":{"1000":1200}})
        self.assertEqual(result["rows"][0]["daily_volume_shares"],1200)
        self.assertIsNone(result["rows"][1]["daily_volume_shares"])
        self.assertFalse(result["rows"][2]["daily_volume_verified"])
    def test_partial_market_source(self):
        def fetcher(market):
            if market=="TWSE":return twse()
            raise ValueError("FORBIDDEN")
        result=collect_and_enrich(merged(),fetcher)
        self.assertEqual(result["volume_source_status"],{"TWSE":"VERIFIED","TPEx":"UNAVAILABLE"})
        self.assertFalse(any(r["trade_eligible"] for r in result["rows"]))
    def test_both_market_volume_with_missing_symbol(self):
        result=collect_and_enrich(merged(),lambda market:twse() if market=="TWSE" else tpex())
        self.assertEqual(result["rows"][0]["daily_volume_shares"],1000)
        self.assertEqual(result["rows"][1]["daily_volume_shares"],500)
        self.assertIsNone(result["rows"][2]["daily_volume_shares"])

if __name__=="__main__": unittest.main()
