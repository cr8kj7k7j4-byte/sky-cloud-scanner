import copy
import unittest
from research.sky_p0r_512_source_adapter import adapt, ACCEPTED_RUN, ACCEPTED_SHA, ACCEPTED_ARTIFACT

def fixture():
    samples=[]
    for symbol, exchange in (("2409","TWSE"),("5202","TPEx")):
        candles=[]
        for minute in (0,5,10):
            candles.append({"date":f"2026-11-11T09:{minute:02d}:00+08:00",
                "open":25,"high":26,"low":24,"close":25,"volume":1})
        samples.append({"symbol":symbol,"exchange":exchange,
            "raw_five_min_candles":{"symbol":symbol,"exchange":exchange,
                "timeframe":"5","data":candles},
            "valid_today_five_min_bars":2,
            "excluded_unfinished_five_min_bars":1,
            "rejected_future_five_min_bars":0,
            "last_feature_bar_time_tpe":"2026-11-11T09:05:00+08:00",
            "bar_sequence_valid":True})
    return {"schema":"SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1",
        "head_sha":ACCEPTED_SHA,"run_id":ACCEPTED_RUN,
        "time_tpe":"2026-11-11T09:11:00+08:00",
        "stage2_quote_verified":False,"production_eligible":False,
        "automatic_order":False,"samples":samples}
def run(data):
    return adapt(data,actual_run=ACCEPTED_RUN,actual_sha=ACCEPTED_SHA,
                 artifact_id=ACCEPTED_ARTIFACT)
class SourceAdapterTests(unittest.TestCase):
    def test_verified_completed_bars_never_generate_fills(self):
        x=run(fixture())
        self.assertEqual(x["verdict"],"BARS_VERIFIED_PRECOMMITTED_SIGNAL_MISSING")
        self.assertEqual(x["paper_fill_count"],0)
        self.assertFalse(x["production_eligible"])
        self.assertEqual(x["bar_sources"]["2409"]["accepted_count"],2)
    def test_wrong_artifact_provenance_rejected(self):
        with self.assertRaisesRegex(ValueError,"PROVENANCE"):
            adapt(fixture(),actual_run=ACCEPTED_RUN,actual_sha=ACCEPTED_SHA,artifact_id="fake")
    def test_unfinished_bar_cannot_be_counted(self):
        x=fixture()
        x["samples"][0]["valid_today_five_min_bars"]=3
        with self.assertRaisesRegex(ValueError,"COUNTS"):
            run(x)
    def test_future_and_out_of_order_fails_closed(self):
        x=fixture()
        x["samples"][0]["raw_five_min_candles"]["data"][1]["date"]="2026-11-11T09:00:00+08:00"
        with self.assertRaisesRegex(ValueError,"OUT_OF_ORDER"):
            run(x)
    def test_future_source_requires_independent_github_attestation(self):
        new_run, new_sha, new_artifact = "98765432", "a"*40, "45678"
        payload = fixture()
        payload["run_id"] = new_run
        payload["head_sha"] = new_sha
        receipt = {"github_run_verified": True,
                   "successful_completed_run": True,
                   "unique_artifact_verified": True,
                   "source_workflow_matches_accepted": True,
                   "production_eligible": False,
                   "run_id": new_run, "head_sha": new_sha,
                   "artifact_id": new_artifact}
        with self.assertRaisesRegex(ValueError,"PROVENANCE"):
            adapt(payload,actual_run=new_run,actual_sha=new_sha,artifact_id=new_artifact)
        out = adapt(payload,actual_run=new_run,actual_sha=new_sha,
                    artifact_id=new_artifact,verified_future_source=receipt)
        self.assertTrue(out["github_bar_source_verified"])
        self.assertEqual(out["source_run_id"],new_run)
        self.assertEqual(out["paper_fill_count"],0)
        self.assertFalse(out["production_eligible"])
        for field in ("github_run_verified","successful_completed_run",
                      "unique_artifact_verified","source_workflow_matches_accepted"):
            bad = dict(receipt)
            bad[field] = False
            with self.subTest(field=field), self.assertRaisesRegex(
                    ValueError,"UNVERIFIED_FUTURE_BAR_SOURCE"):
                adapt(payload,actual_run=new_run,actual_sha=new_sha,
                      artifact_id=new_artifact,verified_future_source=bad)
        bad = dict(receipt)
        bad["artifact_id"] = "forged"
        with self.assertRaisesRegex(ValueError,"PROVENANCE"):
            adapt(payload,actual_run=new_run,actual_sha=new_sha,
                  artifact_id=new_artifact,verified_future_source=bad)

    def test_no_production_promotion(self):
        x=fixture()
        x["production_eligible"]=True
        with self.assertRaisesRegex(ValueError,"UNTRUSTED"):
            run(x)
if __name__=="__main__":
    unittest.main()
