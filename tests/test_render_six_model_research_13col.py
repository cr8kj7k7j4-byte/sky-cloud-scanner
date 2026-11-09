import unittest

from research.render_six_model_research_13col import COLUMNS, render


class ResearchDisplayTests(unittest.TestCase):
    def test_missing_signals_have_exact_user_placeholder(self):
        output = render({"records": [], "market_data_gate": "BLOCKED_EXTERNAL_DATA"})
        self.assertEqual(len(output["columns"]), 13)
        self.assertEqual(output["columns"], list(COLUMNS))
        self.assertEqual(output["rows"], [[
            "—", "暫無合格候選", "待確認", "X", "不交易",
            "—", "—", "待確認", "待確認", "待確認",
            "等待", "待確認", "待確認",
        ]])
        self.assertFalse(output["production_eligible"])

    def test_observation_present_even_when_market_gate_blocks(self):
        record = {
            "symbol": "2330", "name": "台積電",
            "status": "RESEARCH_OBSERVATION",
            "reference_executed_price": 888,
            "quote_date": "2026-11-09", "quote_time": "11:50:00",
            "direction": "偏多",
        }
        output = render({"records": [record], "market_data_gate": "BLOCKED_EXTERNAL_DATA"})
        self.assertEqual(output["rows"][0][2], "888")
        self.assertEqual(output["rows"][0][3], "X")
        self.assertEqual(output["rows"][0][10], "觀察")
        self.assertEqual(output["rows"][0][5], "—")
        self.assertEqual(output["rows"][0][7], "待確認")
        self.assertIn("禁止新進場", output["markdown"])

    def test_unverified_price_is_not_misrepresented_as_live(self):
        output = render({"records": [{
            "symbol": "1101", "status": "INSUFFICIENT_EXECUTION_EVIDENCE",
            "reference_executed_price": 23,
            "direction": "偏多",
        }]})
        self.assertEqual(output["rows"][0][2], "待確認")
        self.assertEqual(output["rows"][0][4], "不交易")

    def test_missing_execution_timestamp_does_not_claim_live(self):
        output = render({"records": [{
            "symbol": "1101", "status": "RESEARCH_OBSERVATION",
            "reference_executed_price": 23,
            "quote_date": "2026-11-09", "quote_time": None,
        }]})
        self.assertEqual(output["rows"][0][2], "待確認")

    def test_bad_record_collection_is_rejected(self):
        with self.assertRaises(ValueError):
            render({"records": "fake"})


if __name__ == "__main__":
    unittest.main()
