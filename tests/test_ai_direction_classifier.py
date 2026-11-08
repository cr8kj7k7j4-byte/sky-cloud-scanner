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

    def test_horizon_is_never_production(self):
        import inspect
        from research.ai_direction_classifier import train
        self.assertIn('"production_eligible":False', inspect.getsource(train))
        self.assertIn('"probabilities_verified":False', inspect.getsource(train))


if __name__ == "__main__":
    unittest.main()
