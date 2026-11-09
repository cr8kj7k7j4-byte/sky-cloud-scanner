"""Safety checks for Sky fixed 13-column informational output."""
import unittest
from research.sky_information_13col import COLUMNS, build, markdown


class TestInformation13Columns(unittest.TestCase):
    def test_fixed_schema_and_unverified_price(self):
        view = build({"checked_at_tpe": "2026-11-09T11:00:00+08:00",
                      "universe_count": 2, "observed_price_count": 1,
                      "fresh_executed_count": 0,
                      "all_symbols": [
                          {"symbol": "1234", "name": "測試", "last_price": 42.5,
                           "data_status": "UNVERIFIED_EXECUTION_TIME"},
                          {"symbol": "5678", "name": "無價", "last_price": None,
                           "data_status": "MISSING_QUOTE"}]})
        self.assertEqual(len(COLUMNS), 13)
        self.assertEqual(len(view["rows"]), 2)
        self.assertEqual(view["rows"][0]["即時價"], "觀察價 42.50（未驗證）")
        self.assertEqual(view["rows"][1]["即時價"], "待確認")
        self.assertFalse(view["production_eligible"])
        self.assertEqual(view["rows"][0]["現在動作"], "禁止交易")
        self.assertEqual(view["rows"][0]["多方評分"], "—")
        for title in COLUMNS:
            self.assertIn(title, markdown(view, view["rows"]))

    def test_confirmed_trade_is_displayed_without_observation_label(self):
        view = build({"all_symbols": [{"symbol": "1111", "name": "新鮮",
                       "last_price": 55, "data_status": "FRESH_EXECUTED_TRADE"}]})
        self.assertEqual(view["rows"][0]["即時價"], "55.00")
        self.assertEqual(view["rows"][0]["分類"], "X")
        self.assertEqual(view["rows"][0]["方向"], "不交易")

    def test_empty_result_is_explicit(self):
        view = build({"all_symbols": []})
        self.assertEqual(view["rows"][0]["股票名稱"], "暫無合格候選")
        self.assertEqual(view["rows"][0]["現在動作"], "等待")


if __name__ == "__main__":
    unittest.main()
