import tempfile
import unittest
from pathlib import Path
from research.six_model_preflight import audit, inventory


class SixModelPreflightTest(unittest.TestCase):
    def test_registry_discovery_does_not_assert_six_models(self):
        reg = """## Production baselines
| Type | System / Model | Status | Notes |
|---|---|---|---|
| Production | Day v1.4 | ACTIVE | notes |
## Active research candidates
| Candidate | Status | Priority | Current evidence |
|---|---|---|---|
| Swing 5D | HOLD | 3 | none |
## Evidence-only features
"""
        got = inventory(reg)
        self.assertEqual(len(got["production_baselines"]), 1)
        self.assertEqual(len(got["research_candidates"]), 1)

    def test_missing_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            got = audit(Path(d))
            self.assertEqual(got["status"], "INSUFFICIENT_DATA")
            self.assertFalse(got["historic_backtest_executed"])
            self.assertFalse(got["production_changed"])
            self.assertIn("SIX_MODEL_INDEPENDENT_PROVENANCE_UNVERIFIED",
                          got["blocking_reasons"])

    def test_non_trading_end_date_and_no_claims(self):
        with tempfile.TemporaryDirectory() as d:
            got = audit(Path(d))
            self.assertTrue(got["requested_period"]["end_is_non_trading_day"])
            self.assertFalse(got["fugle_api_called"])
            self.assertFalse(got["six_model_signal_activation"])


if __name__ == "__main__":
    unittest.main()
