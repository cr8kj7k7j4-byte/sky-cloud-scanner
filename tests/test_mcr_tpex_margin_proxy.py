import unittest
from datetime import datetime, timezone, timedelta
from research.mcr_tpex_margin_proxy import build_tpex_proxy
TW=timezone(timedelta(hours=8))
def sample(n=360,day="1151106"):
    return [{"資料日期":day,"代號":str(4000+i),"名稱":"測試","前資餘額":"1,200",
             "資餘額":"1,000"} for i in range(n)]
class TpexTests(unittest.TestCase):
    def test_valid_source(self):
        r=build_tpex_proxy(sample(),now=datetime(2026,11,8,tzinfo=TW))
        self.assertEqual(r["total"],360)
        self.assertEqual(r["margin_data_date"],"2026-11-06")
        self.assertFalse(r["maintenance_below_130_verified"])
        self.assertTrue(all(x["action"]=="觀察" and not x["trade_eligible"] for x in r["rows"]))
    def test_stale(self):
        with self.assertRaisesRegex(ValueError,"STALE"):
            build_tpex_proxy(sample(),now=datetime(2026,11,20,tzinfo=TW))
    def test_missing(self):
        rows=sample()
        rows[0].pop("資料日期")
        with self.assertRaisesRegex(ValueError,"REQUIRED_FIELD"):
            build_tpex_proxy(rows,now=datetime(2026,11,8,tzinfo=TW))
    def test_duplicate(self):
        rows=sample()
        rows[1]["代號"]="4000"
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            build_tpex_proxy(rows,now=datetime(2026,11,8,tzinfo=TW))
    def test_low_coverage(self):
        with self.assertRaisesRegex(ValueError,"INCOMPLETE"):
            build_tpex_proxy(sample(20),now=datetime(2026,11,8,tzinfo=TW))
if __name__=="__main__":unittest.main()
