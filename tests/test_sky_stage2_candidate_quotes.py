import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.sky_stage2_candidate_quotes import select, verify

NOW = datetime(2026,11,10,9,50,0,tzinfo=ZoneInfo("Asia/Taipei"))


def payload():
    return {"date":"2026-11-10", "lastTrade":{
        "price": 55.0, "time":"2026-11-10T09:49:30+08:00"}}


class Stage2BridgeTests(unittest.TestCase):
    def stage1(self):
        return {"schema":"SKY_STAGE1_FUGLE_SNAPSHOT_CANDIDATES_V1",
                "candidate_count":100, "candidates":[
                  {"symbol":str(1101+i), "exchange":"TWSE",
                   "observed_price":55.0, "production_eligible":False} for i in range(10)
                ]+[{"symbol":str(8001+i), "exchange":"TPEx",
                     "observed_price":55.0, "production_eligible":False} for i in range(10)]}

    def test_balanced_and_bounded(self):
        picked = select(self.stage1())
        self.assertEqual(len(picked),6)
        self.assertEqual([r["exchange"] for r in picked],["TWSE"]*3+["TPEx"]*3)

    def test_fresh_trade_still_research_only(self):
        r=verify(self.stage1(),quote_fn=lambda _:payload(),sleep_fn=lambda _:None,now_fn=lambda:NOW)
        self.assertEqual(r["verified_executed_count"],6)
        self.assertFalse(r["production_eligible"])
        self.assertFalse(r["rate_limit_plan_verified"])
        self.assertTrue(all(x["action"]=="等待" for x in r["results"]))

    def test_missing_trade_time_cannot_verify(self):
        q={"date":"2026-11-10","lastTrade":{"price":50.0}}
        r=verify(self.stage1(),quote_fn=lambda _:q,sleep_fn=lambda _:None,now_fn=lambda:NOW)
        self.assertEqual(r["verified_executed_count"],0)

    def test_429_stops_queries(self):
        import requests
        def rejected(_):
            response = requests.Response()
            response.status_code=429
            raise requests.HTTPError("rate limited",response=response)
        r=verify(self.stage1(),quote_fn=rejected,sleep_fn=lambda _:None,now_fn=lambda:NOW)
        self.assertEqual(r["attempted_count"],1)
        self.assertEqual(r["rate_limited_count"],1)

    def test_cannot_expand_beyond_three_per_market(self):
        with self.assertRaisesRegex(ValueError,"INVALID_SAMPLE_SIZE"):
            select(self.stage1(),per_market=999)

if __name__=="__main__":
    unittest.main()
