import unittest
from src.sky_thirteen_column_report import COLUMNS, render_sky_table

class SkyThirteenColumnReportTest(unittest.TestCase):
    def test_empty_placeholder_has_thirteen_columns(self):
        result = render_sky_table([], source="Fugle", observed_at="unknown")
        lines = result.splitlines()
        self.assertEqual(len(COLUMNS), 13)
        self.assertEqual(len(lines[-1].split("|")) - 2, 13)
        self.assertIn("暫無合格候選", result)

    def test_preserves_partial_observations_without_fake_execution(self):
        data = [{"股票代碼": "1234", "股票名稱": "示例", "即時價": 99,
                 "多方評分": None, "現在動作": "買進"}]
        result = render_sky_table(data, source="snapshot", trade_eligible=False)
        self.assertIn("1234", result)
        self.assertIn("待確認", result)
        self.assertIn("禁止交易", result)
        self.assertNotIn("| 99 |", result)

    def test_verified_quote_and_scores(self):
        data = [{"股票代碼": "1234", "股票名稱": "示例", "即時價": 42.3,
                 "executed_trade_verified": True, "多方評分": 72,
                 "空方評分": 25, "現在動作": "觀察"}]
        result = render_sky_table(data, source="executed", observed_at="2026-11-09",
                                  verified_executions=True)
        self.assertIn("| 42.3 |", result)
        self.assertIn("| 72 | 25 |", result)

if __name__ == "__main__":
    unittest.main()
