"""Fail-closed postmarket acceptance tests, no external services."""
import unittest

from research.sky_postmarket_acceptance import COLUMNS, data_checks, overall, workflow_state


class AcceptanceTests(unittest.TestCase):
    def test_missing_run(self):
        self.assertEqual(workflow_state([]), "NOT_VERIFIED")
        self.assertEqual(workflow_state(None, "HTTPError"), "NOT_VERIFIED")

    def test_workflow_success_is_only_process_pass(self):
        self.assertEqual(workflow_state([{"status": "completed", "conclusion": "success"}]), "PROCESS_PASS")
        self.assertEqual(workflow_state([{"status": "completed", "conclusion": "failure"}]), "FAIL")

    def test_missing_market_data_never_passes(self):
        values = data_checks(None)
        self.assertTrue(all(v == "NOT_VERIFIED" for v in values.values()))

    def test_13column_preview_never_certifies_full_artifact(self):
        row = {name: "待確認" for name in COLUMNS}
        data = {"universe_count": 1, "row_count": 1, "preview": [row],
                "observed_price_count": 1, "fresh_executed_count": 0,
                "production_eligible": False}
        values = data_checks(data)
        self.assertEqual(values["13欄報告"], "PREVIEW_PASS_FULL_ARTIFACT_NOT_VERIFIED")
        self.assertEqual(values["有效成交驗證"], "ZERO_VERIFIED")
        self.assertEqual(values["正式交易資格"], "BLOCKED")
        self.assertEqual(overall(values), "NOT_VERIFIED")

    def test_absent_column_rejected(self):
        row = {name: "待確認" for name in COLUMNS[:-1]}
        data = {"universe_count": 1, "row_count": 1, "preview": [row]}
        self.assertEqual(data_checks(data)["13欄報告"], "NOT_VERIFIED")

    def test_fail_is_not_masked(self):
        self.assertEqual(overall({"scan": "FAIL", "other": "PROCESS_PASS"}), "FAIL")


if __name__ == "__main__":
    unittest.main()
