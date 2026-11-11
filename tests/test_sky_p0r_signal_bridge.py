"""No-provider signal-to-paper provenance tests. No fabricated fills."""
import copy
import unittest
from research.sky_p0r_signal_bridge import join


def bars():
    return {
        "schema":"SKY_P0R_VERIFIED_SOURCE_BARS_V1",
        "source_run_id":"42950211804",
        "source_sha":"b9e2f57b02b6c22b0f45d3fb7ae21e2a1cca0ac0",
        "source_artifact_id":"13824108931",
        "observed_at":"2026-11-11T11:04:04+08:00",
        "market_bars_available":True,
        "production_eligible":False, "automatic_order":False,
        "bar_sources":{"2409":{"exchange":"TWSE","completed_bars":[{
            "symbol":"2409","source_type":"MARKET_OBSERVATION",
            "source_artifact":"sky-512-5m-evidence-42950211804:13824108931",
            "started_at":"2026-11-11T10:55:00+08:00",
            "completed_at":"2026-11-11T11:00:00+08:00",
            "open":20,"high":20.3,"low":19.9,"close":20.1
        }]}}
    }


def signal():
    return {"schema":"SKY_PRECOMMITTED_PAPER_SIGNAL_V1",
        "signal_run_id":"42955503328",
        "signal_sha":"0d3548bb83d9556d65aac6a7dc7ebc3e3ab64f03",
        "signal_artifact_id":"13826921865",
        "signal_scan_id":"42955503328",
        "published_at":"2026-11-11T11:52:00+08:00",
        "production_eligible":False,"automatic_order":False,
        "signal":{"market_scan_id":"42955503328",
                  "signal_id":"not-a-real-signal-unit-test",
                  "signal_time":"2026-11-11T11:52:00+08:00",
                  "symbol":"2409"}}


class SignalPaperBridgeTests(unittest.TestCase):
    def test_missing_signal_is_explicit_hold(self):
        status,payload=join(bars(),None)
        self.assertEqual(status["reason"],"PRECOMMITTED_SIGNAL_ARTIFACT_MISSING")
        self.assertEqual(status["paper_fill_count"],0)
        self.assertIsNone(payload)
        self.assertFalse(status["reconciled"])
    def test_later_scan_must_not_backfill_earlier_candles(self):
        status,payload=join(bars(),signal())
        self.assertEqual(status["reason"],"SIGNAL_PUBLISHED_AFTER_BAR_OBSERVATION")
        self.assertEqual(status["paper_events_produced"],0)
        self.assertIsNone(payload)
    def test_claimed_signal_provenance_cannot_force_paper_fills(self):
        data=signal()
        data["published_at"]=data["signal"]["signal_time"]="2026-11-11T10:40:00+08:00"
        data["independently_verified"]=True  # Untrusted caller assertion.
        result,payload=join(bars(),data)
        self.assertEqual(result["reason"],"SIGNAL_ARTIFACT_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(result["paper_fill_count"],0)
        self.assertIsNone(payload)

    def test_unknown_symbol_cannot_be_paper_filled(self):
        data=signal()
        data["published_at"]=data["signal"]["signal_time"]="2026-11-11T10:40:00+08:00"
        data["signal"]["symbol"]="9999"
        status,_=join(bars(),data,external_signal_provenance_verified=True)
        self.assertEqual(status["reason"],"SIGNAL_SYMBOL_NOT_IN_VERIFIED_BARS")
    def test_missing_completed_future_bar_fails_closed(self):
        data=signal()
        data["published_at"]=data["signal"]["signal_time"]="2026-11-11T10:58:00+08:00"
        status,_=join(bars(),data,external_signal_provenance_verified=True)
        self.assertEqual(status["reason"],"NO_CANDLE_START_AFTER_SIGNAL_PUBLICATION")
    def test_mutated_scan_id_rejected(self):
        data=signal()
        data["signal"]["market_scan_id"]="foreign"
        with self.assertRaisesRegex(ValueError,"SIGNAL_SCAN_ID_MISMATCH"):
            join(bars(),data)
    def test_future_bar_is_rejected(self):
        data=copy.deepcopy(bars())
        data["bar_sources"]["2409"]["completed_bars"][0]["completed_at"]="2026-11-11T11:15:00+08:00"
        s=signal()
        s["published_at"]=s["signal"]["signal_time"]="2026-11-11T10:40:00+08:00"
        with self.assertRaisesRegex(ValueError,"FUTURE_OR_INCOMPLETE_BARS"):
            join(data,s,external_signal_provenance_verified=True)
    def test_synthetic_bars_do_not_elevate_production(self):
        bad=bars()
        bad["production_eligible"]=True
        with self.assertRaisesRegex(ValueError,"UNTRUSTED_MARKET_BARS"):
            join(bad,None)


if __name__=="__main__":
    unittest.main()
