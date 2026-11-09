import unittest
from datetime import datetime, date
from zoneinfo import ZoneInfo
from src.sky_global_premarket import render, freshness, previous_weekday


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 2, 8, tzinfo=ZoneInfo('Asia/Taipei'))

    def test_night_session_uses_previous_weekday_not_report_date(self):
        self.assertEqual(date(2026, 11, 6), previous_weekday(date(2026, 11, 9)))
        self.assertEqual(date(2026, 11, 9), previous_weekday(date(2026, 11, 10)))
        self.assertEqual(date(2026, 11, 6), previous_weekday(date(2026, 11, 8)))

    def test_missing_data_is_not_treated_as_safe(self):
        report = render({'source_status': 'PASS', 'market_open': True}, {}, self.now)
        self.assertIn('台指期夜盤：待確認', report)
        self.assertIn('美國10年公債殖利率：待確認', report)
        self.assertIn('不得將資料缺漏視為利多或低風險', report)

    def test_calendar_error_fails_closed(self):
        report = render({'source_status': 'WARN', 'market_open': True}, {}, self.now)
        self.assertIn('無法確認開市', report)
        self.assertNotIn('台指期夜盤', report)

    def test_closed_day_does_not_interpret_market(self):
        report = render({'source_status': 'PASS', 'market_open': False}, {}, self.now)
        self.assertIn('台股休市', report)
        self.assertNotIn('台指期夜盤', report)

    def test_value_needs_provenance(self):
        report = render({'source_status': 'PASS', 'market_open': True}, {'vix': {'value': 17}}, self.now)
        self.assertIn('VIX：待確認', report)

    def test_aged_data_is_flagged(self):
        self.assertIn('可能過期', freshness('2026-10-29', self.now))
        self.assertIn('最新交易日仍待確認', freshness('2026-10-30', self.now))
        self.assertEqual('日期無法確認', freshness('2026-11-03', self.now))


if __name__ == '__main__':
    unittest.main()
