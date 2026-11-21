import copy
import unittest

from research.sky_independent_five_min_source_proof import validate

SHA = "a" * 40


def fixture():
    run = {"id": 123, "head_sha": SHA, "status": "completed",
           "conclusion": "success", "repository": {"full_name": "cr8kj7k7j4-byte/sky-cloud-scanner"}}
    artifact = {"id": 456, "expired": False, "workflow_run": {"id": 123},
                "created_at": "2026-11-23T03:00:00+00:00"}
    bars = [
        {"date": f"2026-11-23T10:{m:02d}:00+08:00",
         "open": 30, "high": 31, "low": 29, "close": 30, "volume": 100}
        for m in (0, 5)
    ]
    receipt = {"schema": "SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1",
               "run_id": "123", "head_sha": SHA, "time_tpe": "2026-11-23T10:11:00+08:00",
               "production_eligible": False, "automatic_order": False,
               "samples": [{"symbol": "2409", "exchange": "TWSE",
                            "raw_five_min_candles": {"symbol": "2409", "exchange": "TWSE",
                                                     "timeframe": "5", "data": bars},
                            "valid_today_five_min_bars": 2,
                            "excluded_unfinished_five_min_bars": 0,
                            "rejected_future_five_min_bars": 0,
                            "bar_sequence_valid": True,
                            "last_feature_bar_time_tpe": "2026-11-23T10:05:00+08:00"}]}
    return receipt, run, artifact


class IndependentFiveMinProofTests(unittest.TestCase):
    def test_valid_read_only_evidence_never_certifies_trading(self):
        p, r, a = fixture()
        result = validate(p, run=r, artifact=a)
        self.assertEqual(result["samples"][0]["completed_bars"], 2)
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["automatic_order"])
        self.assertFalse(result["bar_timestamp_semantics_certified"])
        self.assertFalse(result["github_metadata_independently_fetched_by_this_module"])

    def test_mismatched_run_sha_artifact_and_untrusted_run(self):
        for part, key, value in (("receipt", "run_id", "124"),
                                 ("receipt", "head_sha", "b" * 40),
                                 ("run", "conclusion", "failure"),
                                 ("artifact", "expired", True)):
            p, r, a = fixture()
            {"receipt": p, "run": r, "artifact": a}[part][key] = value
            with self.subTest(part=part, key=key), self.assertRaises(ValueError):
                validate(p, run=r, artifact=a)

    def test_bar_grid_order_date_ohlc_and_volume(self):
        for key, value in (("date", "2026-11-23T10:06:00+08:00"),
                           ("open", float("nan")), ("volume", -1),
                           ("low", 32)):
            p, r, a = fixture()
            p["samples"][0]["raw_five_min_candles"]["data"][1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(p, run=r, artifact=a)

    def test_reject_incorrect_counts(self):
        p, r, a = fixture()
        p["samples"][0]["valid_today_five_min_bars"] = 3
        with self.assertRaisesRegex(ValueError, "COUNTS"):
            validate(p, run=r, artifact=a)

    def test_exclude_unfinished_bar(self):
        p, r, a = fixture()
        p["time_tpe"] = "2026-11-23T10:08:00+08:00"
        p["samples"][0]["valid_today_five_min_bars"] = 1
        p["samples"][0]["excluded_unfinished_five_min_bars"] = 1
        p["samples"][0]["last_feature_bar_time_tpe"] = "2026-11-23T10:00:00+08:00"
        result = validate(p, run=r, artifact=a)
        self.assertEqual(result["samples"][0]["excluded_unfinished"], 1)

    def test_reject_unfinished_claimed_completed(self):
        p, r, a = fixture()
        p["time_tpe"] = "2026-11-23T10:08:00+08:00"
        with self.assertRaises(ValueError):
            validate(p, run=r, artifact=a)

    def test_reject_missing_metadata(self):
        p, _, a = fixture()
        with self.assertRaises(ValueError):
            validate(p, run=None, artifact=a)


if __name__ == "__main__":
    unittest.main()
