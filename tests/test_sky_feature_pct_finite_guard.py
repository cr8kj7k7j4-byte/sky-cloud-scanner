"""Offline regression checks for finite research feature percentage ratios."""
import math
import unittest

from src.feature_engine import _safe_pct, build_features


class FeaturePercentFiniteGuardTests(unittest.TestCase):
    def test_normal_percentage_unchanged(self):
        self.assertAlmostEqual(_safe_pct(105, 100), 5.0)

    def test_malformed_and_nonfinite_percentages_fail_closed(self):
        cases = [
            (None, 100), (100, None), (100, 0),
            ("N/A", 100), (100, "N/A"), (True, 100),
            (100, False), (float("nan"), 100),
            (100, float("inf")), (float("inf"), 100),
            (1e308, 1e-308), (1e308, 1),
        ]
        for numerator, denominator in cases:
            with self.subTest(numerator=numerator, denominator=denominator):
                self.assertIsNone(_safe_pct(numerator, denominator))

    def test_extreme_provider_average_does_not_pollute_vwap_preview(self):
        features = build_features({"last": 1e308, "avg_price": 1e-308})
        self.assertIsNone(features.vwap_distance_pct)
        self.assertIsNone(features.momentum_1)
        self.assertIsNone(features.momentum_5)


if __name__ == "__main__":
    unittest.main()
