import copy
import hashlib
import json
import unittest

from research.sky_p0r_market_event_producer import produce, source_binding_verified, signal_import_status_verified

def bar(start, finish, open_price, high, low, close):
    return {"symbol":"2409", "source_type":"MARKET_OBSERVATION",
            "source_artifact":"MARKET_UNIT_TEST_ONLY",
            "started_at":"2026-11-11T"+start+"+08:00",
            "completed_at":"2026-11-11T"+finish+"+08:00",
            "open":open_price,"high":high,"low":low,"close":close}

SOURCE={
    "context":{"run_id":"UNIT_TEST","scan_id":"scan-test",
               "source_artifact":"MARKET_UNIT_TEST_ONLY",
               "simulator_version":"UNIT_TEST",
               "observed_at":"2026-11-11T09:30:00+08:00"},
    "signal":{"symbol":"2409","signal_id":"signal-1","market_scan_id":"scan-test",
              "signal_time":"2026-11-11T09:05:00+08:00",
              "candidate":{"entry":25,"stop":24,"target":28,"grade":"A+"},
              "shares":1000,
              "execution_assumptions":{"entry_slippage_bps":5,
                  "exit_slippage_bps":5,"spread_bps":5,
                  "liquidity_penalty_bps":5,"fill_probability":0.8}},
    "completed_bars":[
        bar("09:10:00","09:15:00",25,25.4,24.8,25.3),
        bar("09:15:00","09:20:00",25.3,28.2,25.2,28.1),
        bar("09:20:00","09:25:00",27.8,28.0,27.5,27.6)]
}

class MarketEventProducerTest(unittest.TestCase):
    def test_current_signal_import_status_must_match_source_binding(self):
        proof={"github_metadata_verified":True,
               "signal_run_id":"999", "signal_sha":"s"*40,
               "signal_artifact_id":"888",
               "artifact_uploaded_at":"2026-11-11T09:05:00+08:00",
               "effective_published_at":"2026-11-11T09:05:00+08:00"}
        binding={"signal_provenance":copy.deepcopy(proof), "market_run_id":"456"}
        good={"reconciled":True,"production_eligible":False,
              "automatic_order":False,"verified_github_provenance":copy.deepcopy(proof),
              "signal_source_run_id":"999", "bar_source_run_id":"456"}
        self.assertTrue(signal_import_status_verified(good,binding))
        for bad in (
            None, {}, {**good,"reconciled":False},
            {**good,"production_eligible":True},
            {**good,"verified_github_provenance":{}},
            {**good,"verified_github_provenance":{**proof,"signal_run_id":"OLD"}},
            {**good,"verified_github_provenance":{**proof,"github_metadata_verified":False}},
            {**good,"signal_source_run_id":"OTHER_SIGNAL_RUN"},
            {**good,"bar_source_run_id":"OTHER_MARKET_RUN"},
            {**good,"bar_source_run_id":None},
        ):
            with self.subTest(bad=bad):
                self.assertFalse(signal_import_status_verified(bad,binding))
        self.assertFalse(signal_import_status_verified(good,None))

    def test_paper_source_binding_rejects_unproven_and_mutated_payload(self):
        payload=copy.deepcopy(SOURCE)
        payload["context"]["run_id"]="12345"
        payload["context"]["source_artifact"]="sky-512-5m-evidence-12345:67890"
        for bar in payload["completed_bars"]:
            bar["source_artifact"]=payload["context"]["source_artifact"]
        payload["signal"]["signal_time"]="2026-11-11T09:05:00+08:00"
        bars={"schema":"SKY_P0R_VERIFIED_SOURCE_BARS_V1",
              "source_run_id":"12345","source_sha":"fixture-sha",
              "source_artifact_id":"67890",
              "observed_at":payload["context"]["observed_at"],
              "production_eligible":False,"automatic_order":False,
              "bar_sources":{"2409":{"completed_bars":payload["completed_bars"]}}}
        digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,
            sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()
        binding={"schema":"SKY_P0R_PAPER_SOURCE_BINDING_V1",
                 "paper_input_sha256":digest,
                 "market_run_id":"12345","market_sha":"fixture-sha",
                 "market_artifact_id":"67890",
                 "market_observed_at":payload["context"]["observed_at"],
                 "signal_provenance":{"github_metadata_verified":True,
                     "signal_run_id":"999","signal_sha":"fixture-signal-sha",
                     "signal_artifact_id":"888",
                     "artifact_uploaded_at":"2026-11-11T09:05:00+08:00",
                     "effective_published_at":"2026-11-11T09:05:00+08:00"},
                 "production_eligible":False,"automatic_order":False}
        self.assertTrue(source_binding_verified(payload,binding,bars))
        self.assertFalse(source_binding_verified(payload,None,bars))
        self.assertFalse(source_binding_verified(payload,binding,None))
        altered=copy.deepcopy(payload)
        altered["completed_bars"][0]["close"]+=0.1
        self.assertFalse(source_binding_verified(altered,binding,bars))
        wrong=copy.deepcopy(binding)
        wrong["signal_provenance"]["github_metadata_verified"]=False
        self.assertFalse(source_binding_verified(payload,wrong,bars))
        wrong=copy.deepcopy(binding)
        wrong["signal_provenance"]["effective_published_at"]="2026-11-11T09:10:00+08:00"
        self.assertFalse(source_binding_verified(payload,wrong,bars))

    def test_completed_future_bars_produce_reconciled_paper_only_estimates(self):
        report=produce(SOURCE)
        self.assertEqual(report["verdict"],"PAPER_EVENT_CHAIN_RECONCILED_ORIGIN_UNVERIFIED")
        self.assertEqual(len(report["events"]),4)
        self.assertEqual(report["snapshot"]["open_positions"],0)
        self.assertTrue(report["ledger_audit"]["reconciled"])
        self.assertFalse(report["market_source_independently_verified"])
        self.assertFalse(report["production_eligible"])
        self.assertEqual(report["events"][1]["event_time"],"2026-11-11T09:10:00+08:00")
        self.assertEqual(report["events"][3]["event_time"],"2026-11-11T09:20:00+08:00")

    def test_no_following_exit_bar_no_fabricated_fill(self):
        d=copy.deepcopy(SOURCE)
        d["completed_bars"]=d["completed_bars"][:2]
        self.assertEqual(produce(d)["events"],[])

    def test_price_gap_causes_no_fill(self):
        d=copy.deepcopy(SOURCE)
        d["completed_bars"][0]["open"]=26
        d["completed_bars"][0]["high"]=26.2
        d["completed_bars"][0]["low"]=25
        d["completed_bars"][0]["close"]=25.3
        self.assertEqual(produce(d)["verdict"],"ENTRY_PRICE_NOT_EXECUTABLE_AS_PLANNED")

    def test_reject_intrabar_lookahead_or_false_provenance(self):
        for changes in (
            {"source_artifact":"WRONG"},
            {"started_at":"2026-11-11T09:05:00+08:00"},
            {"completed_at":"2026-11-11T09:45:00+08:00"},
        ):
            d=copy.deepcopy(SOURCE)
            d["completed_bars"][0].update(changes)
            with self.subTest(changes=changes):
                if changes.get("started_at"):
                    # With first bar opening at signal time, no eligible
                    # next-bar sequence => cannot produce a paper trade.
                    self.assertEqual(produce(d)["events"],[])
                else:
                    with self.assertRaises(ValueError):
                        produce(d)

    def test_no_invented_execution_costs(self):
        d=copy.deepcopy(SOURCE)
        del d["signal"]["execution_assumptions"]["spread_bps"]
        with self.assertRaises(ValueError):
            produce(d)

    def test_weak_rr_is_blocked_by_canonical_gate(self):
        d=copy.deepcopy(SOURCE)
        d["signal"]["candidate"]["target"]=25.2
        self.assertEqual(produce(d)["verdict"],"CANONICAL_P0R_P0X_BLOCK")

if __name__=="__main__":
    unittest.main()
