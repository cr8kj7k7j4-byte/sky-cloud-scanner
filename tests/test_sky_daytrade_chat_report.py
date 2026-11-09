import unittest

from src.sky_daytrade_chat_report import COLUMNS, markdown, project


class DaytradeChatReportTest(unittest.TestCase):
    def sample(self):
        return {
            "schema": "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1",
            "checked_at_tpe": "2026-11-09T11:36:00+08:00",
            "universe_count": 2, "observed_price_count": 2,
            "fresh_executed_count": 1, "fresh_executed_pct": 50,
            "ranked_observations": [
                {"symbol": "1234", "name": "新鮮", "last_price": 50,
                 "data_status": "FRESH_EXECUTED_TRADE", "last_trade_time": "2026-11-09T11:35:55+08:00", "source": "Fugle"},
                {"symbol": "5678", "name": "過期", "last_price": 49,
                 "data_status": "UNVERIFIED_EXECUTION_TIME", "last_trade_time": None, "source": "Fugle"}
            ],
        }

    def test_exact_13_columns_and_no_fabricated_levels(self):
        output = project(self.sample())
        self.assertEqual(len(COLUMNS), 13)
        self.assertEqual(output["columns"], list(COLUMNS))
        self.assertEqual(output["rows"][0]["即時價"], "50")
        self.assertEqual(output["rows"][1]["即時價"], "—")
        self.assertEqual(output["rows"][1]["觀察價（未必即時）"], 49)
        for row in output["rows"]:
            self.assertEqual(row["現在動作"], "禁止交易")
            self.assertEqual(row["買進觸發"], "—")
            self.assertEqual(row["多方評分"], "—")
            self.assertEqual(row["停利價格"], "—")
        self.assertFalse(output["production_eligible"])

    def test_empty_and_schema_guard(self):
        sample = self.sample()
        sample["ranked_observations"] = []
        self.assertIn("不能宣稱全市場沒有合格標的", markdown(project(sample)))
        sample["schema"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            project(sample)

    def test_negative_limit_guard(self):
        with self.assertRaises(ValueError):
            project(self.sample(), limit=-1)


if __name__ == "__main__":
    unittest.main()
