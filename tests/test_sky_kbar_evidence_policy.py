"""W0 #363: one canonical zero/sparse/full K-bar research policy."""
import unittest

from src.sky_kbar_evidence_policy import classify, INVALID, NO_BARS, OBSERVED, SPARSE


class KbarTierTests(unittest.TestCase):
    def test_no_bars_does_not_block_other_sourced_research(self):
        x = classify(source_valid=True, observed_bars=0)
        self.assertEqual(x["kbar_evidence_level"], NO_BARS)
        self.assertTrue(x["research_report_available"])
        self.assertFalse(x["five_minute_indicators_available"])
        self.assertFalse(x["independent_vwap_certified"])
        self.assertFalse(x["execution_authorized"])
        self.assertFalse(x["production_eligible"])

    def test_sparse_and_full_observation_do_not_grant_trades(self):
        for n, missing, expected in ((1, 52, SPARSE), (5, 1, SPARSE), (54, 0, OBSERVED)):
            x = classify(source_valid=True, observed_bars=n, missing_slots=missing)
            self.assertEqual(x["kbar_evidence_level"], expected)
            self.assertTrue(x["research_report_available"])
            self.assertTrue(x["five_minute_indicators_available"])
            self.assertFalse(x["session_coverage_certified"])
            self.assertFalse(x["production_eligible"])

    def test_bad_provenance_is_not_overridden_by_count(self):
        for n in (0, 1, 54):
            x = classify(source_valid=False, observed_bars=n)
            self.assertEqual(x["kbar_evidence_level"], INVALID)
            self.assertFalse(x["research_report_available"])
            self.assertFalse(x["five_minute_indicators_available"])

    def test_invalid_count_is_never_silently_coerced(self):
        for count in (-1, True, 1.4, "2"):
            with self.assertRaises(ValueError):
                classify(source_valid=True, observed_bars=count)


if __name__ == "__main__":
    unittest.main()
