import unittest,tempfile
from datetime import datetime,timezone,timedelta
from research.mcr_forward_price_snapshots import collect,write_immutable,parse_market_rows

TZ=timezone(timedelta(hours=8))
NOW=datetime(2026,11,8,7,30,tzinfo=TZ)
def mock(market,day="1151106",bad=False):
    if market=="TWSE":
        return [{"Code":str(1000+i),"Date":day,"ClosingPrice":"12.5"} for i in range(510)]
    return [{"SecuritiesCompanyCode":str(4000+i),"Date":day,"Close":"22.3"} for i in range(350)]

class PriceTests(unittest.TestCase):
    def test_real_schema_and_causal_time(self):
        d=collect("2026-11-06",fetcher=mock,now=NOW)
        self.assertEqual(d["total"],860)
        self.assertEqual(d["market_counts"],{"TWSE":510,"TPEx":350})
        self.assertFalse(d["execution_authorized"])
        self.assertEqual(d["rows"][0]["adjusted"],False)
    def test_bad_date_blocks_cross_market(self):
        with self.assertRaisesRegex(ValueError,"SESSION_MISMATCH"):
            collect("2026-11-05",fetcher=mock,now=NOW)
    def test_missing_close_remains_missing(self):
        def fetcher(m):
            rows=mock(m)
            if m=="TWSE":rows[0]["ClosingPrice"]="--"
            return rows
        d=collect("2026-11-06",fetcher=fetcher,now=NOW)
        self.assertEqual(d["market_counts"]["TWSE"],509)
    def test_immutable_replay(self):
        d=collect("2026-11-06",fetcher=mock,now=NOW)
        with tempfile.TemporaryDirectory() as temp:
            p=write_immutable(d,temp)
            self.assertEqual(p,write_immutable(d,temp))
            altered=collect("2026-11-06",fetcher=mock,now=NOW)
            altered["rows"][0]["close"]=999
            with self.assertRaisesRegex(ValueError,"IMMUTABLE_PRICE_SNAPSHOT_CONFLICT"):
                write_immutable(altered,temp)
    def test_source_date_cannot_be_earlier_than_capture(self):
        with self.assertRaisesRegex(ValueError,"CAPTURED_BEFORE_SOURCE_SESSION"):
            parse_market_rows(mock("TWSE"),"TWSE",captured_at="2026-11-05T19:00:00+08:00")

if __name__=="__main__":unittest.main()
