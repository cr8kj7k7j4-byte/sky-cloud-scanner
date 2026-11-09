import unittest

from research.sky_full_universe_information import (
    DISPLAY_COLUMNS_13, display_row_13, render_13_table,
)


class TestThirteenColumnInformation(unittest.TestCase):
    def test_column_contract(self):
        self.assertEqual(len(DISPLAY_COLUMNS_13), 13)
        self.assertEqual(DISPLAY_COLUMNS_13[0], "股票代碼")
        self.assertEqual(DISPLAY_COLUMNS_13[-1], "停利價格")

    def test_unverified_observation_visible_but_not_live(self):
        row = {"symbol": "1101", "name": "台泥", "last_price": 27.5,
               "data_status": "UNVERIFIED_EXECUTION_TIME"}
        shown = display_row_13(row)
        self.assertIn("觀察價 27.50", shown["即時價"])
        self.assertIn("未驗證", shown["即時價"])
        self.assertEqual(shown["現在動作"], "禁止交易")
        self.assertEqual(shown["多方評分"], "—")
        self.assertEqual(shown["買進觸發"], "待確認")

    def test_fresh_only_when_verified(self):
        row = {"symbol": "1101", "name": "台泥", "last_price": 27.5,
               "data_status": "FRESH_EXECUTED_TRADE"}
        self.assertEqual(display_row_13(row)["即時價"], "27.50")

    def test_missing_observation_has_full_width_placeholder(self):
        output = render_13_table([])
        self.assertEqual(len(output.splitlines()), 3)
        self.assertEqual(output.splitlines()[0].count("|"), 14)
        self.assertIn("暫無合格候選", output)
        self.assertIn("待確認", output)


if __name__ == "__main__":
    unittest.main()
