"""Safety regressions for the independent research-only direction trainer."""
import unittest

from research.ai_direction_classifier import metrics, split_by_session


class DirectionTrainingTests(unittest.TestCase):
    def test_metrics_not_a_win_probability(self):
        self.assertAlmostEqual(metrics([0, 1, 1, 0], [.1, .8, .6, .4])["directional_accuracy_at_0_5"], 1.0)

    def test_invalid_probability_fails(self):
        with self.assertRaises(ValueError):
            metrics([0], [1.2])

    def test_embargo_required(self):
        with self.assertRaises(ValueError):
            split_by_session(None, embargo_sessions=0)

    def test_future_feature_rejected(self):
        import pandas as pd
        dates = pd.date_range("2026-01-02", periods=70, freq="B", tz="Asia/Taipei")
        frame = pd.DataFrame({
            "date": dates,
            "feature_available_at": dates + pd.Timedelta(minutes=1),
            "label_end_at": dates + pd.Timedelta(days=1),
        })
        with self.assertRaisesRegex(ValueError, "lookahead"):
            split_by_session(frame, embargo_sessions=2)

    def test_label_overlap_purged(self):
        import pandas as pd
        dates = pd.date_range("2026-01-02", periods=70, freq="B", tz="Asia/Taipei")
        frame = pd.DataFrame({
            "date": dates,
            "feature_available_at": dates - pd.Timedelta(minutes=1),
            "label_end_at": dates + pd.Timedelta(days=4),
        })
        train, calibration, oos = split_by_session(frame, embargo_sessions=1)
        self.assertLess(train["label_end_at"].max(), calibration["date"].min())
        self.assertLess(calibration["label_end_at"].max(), oos["date"].min())

    def test_missing_causal_timestamps_rejected(self):
        import pandas as pd
        with self.assertRaisesRegex(ValueError, "missing timestamp"):
            split_by_session(pd.DataFrame({"date": pd.date_range("2026-01-02", periods=70, freq="B", tz="UTC")}), embargo_sessions=1)

    def test_horizon_is_never_production(self):
        import inspect
        from research.ai_direction_classifier import train
        self.assertIn('"production_eligible":False', inspect.getsource(train))
        self.assertIn('"probabilities_verified":False', inspect.getsource(train))


if __name__ == "__main__":
    unittest.main()
