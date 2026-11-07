import json
import tempfile
import unittest
from pathlib import Path
from research.six_model_evidence_triage import build_report


class TriageTest(unittest.TestCase):
    def test_missing_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            x=build_report(Path(directory))
            self.assertEqual(x["six_model_ids_independently_verified"],0)
            self.assertEqual(x["history_replay_status"],"INSUFFICIENT_DATA")
            self.assertFalse(x["production_changed"])
            self.assertFalse(x["positive_after_cost_expectancy_certified"])

    def test_algorithm_factory_not_a_model_weight(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"src").mkdir()
            (root/"src/model_training.py").write_text('factories["RANDOM_FOREST"] = lambda: object()')
            x=build_report(root)
            forest=x["ml_algorithm_factories_not_deployed_models"][0]
            self.assertTrue(forest["factory_definition_present"])
            self.assertFalse(forest["trained_weight_verified"])
            self.assertFalse(forest["deployed_decision_model_verified"])

    def test_two_symbol_data_does_not_imply_whole_market(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"docs").mkdir()
            (root/"docs/SKY_FUGLE_2026_HISTORY_PROBE_LATEST.json").write_text(json.dumps({
              "all_symbols_retrieved":True, "results":[{"symbol":"1101"},{"symbol":"8088"}]
            }))
            x=build_report(root)
            self.assertTrue(x["fugle"]["sample_api_data_returned"])
            self.assertFalse(x["fugle"]["full_market_verified"])


if __name__=="__main__":
    unittest.main()
