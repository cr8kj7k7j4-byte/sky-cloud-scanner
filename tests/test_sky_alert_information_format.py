import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from research.sky_full_universe_information import ALERT_COLUMNS, build, summary


class AlertInformationPresentationTest(unittest.TestCase):
    def test_unverified_observation_not_hidden_and_13_columns(self):
        now = datetime(2026, 11, 9, 11, 30, tzinfo=ZoneInfo("Asia/Taipei"))
        universe = [{"symbol": "1234", "name": "測試股", "exchange": "TWSE"}]
        snapshots = {"TSE": {"date": "2026-11-09", "data": [
            {"symbol": "1234", "lastPrice": 55, "tradeVolume": 1234}
        ]}}
        report = build(universe, snapshots, now)
        rendered = summary(report)
        self.assertEqual(len(ALERT_COLUMNS), 13)
        self.assertIn("1234 | 測試股 | 待確認（觀察價 55.00，未驗證）", rendered)
        self.assertIn("1 檔", rendered)
        self.assertEqual(report["fresh_executed_count"], 0)
        self.assertFalse(report["all_symbols"][0]["production_eligible"])
        self.assertEqual(len([x for x in rendered.splitlines() if x.startswith("| 1234")][0].split("|")) - 2, 13)

    def test_empty_report_keeps_requested_columns(self):
        now = datetime(2026, 11, 9, 11, 30, tzinfo=ZoneInfo("Asia/Taipei"))
        report = build([], {}, now)
        rendered = summary(report)
        self.assertIn("暫無可用價格觀察", rendered)
        self.assertIn("加碼價格", rendered)
        self.assertIn("停利價格", rendered)


if __name__ == "__main__":
    unittest.main()
