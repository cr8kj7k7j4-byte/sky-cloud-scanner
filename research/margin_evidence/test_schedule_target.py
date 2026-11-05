import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from research.margin_evidence.schedule_target import scheduled_report_date

TZ = ZoneInfo("Asia/Taipei")


class ScheduledDateTests(unittest.TestCase):
    def test_on_time_friday(self):
        self.assertEqual(str(scheduled_report_date(datetime(2026, 11, 6, 23, 30, tzinfo=TZ))), "2026-11-06")

    def test_delayed_across_midnight(self):
        self.assertEqual(str(scheduled_report_date(datetime(2026, 11, 6, 0, 33, tzinfo=TZ))), "2026-11-05")

    def test_utc_runner_clock(self):
        self.assertEqual(str(scheduled_report_date(datetime(2026, 11, 5, 16, 33, tzinfo=timezone.utc))), "2026-11-05")

    def test_friday_to_saturday(self):
        self.assertEqual(str(scheduled_report_date(datetime(2026, 11, 7, 0, 25, tzinfo=TZ))), "2026-11-06")

    def test_reject_naive_clock(self):
        with self.assertRaises(ValueError):
            scheduled_report_date(datetime(2026, 11, 6, 0, 33))


if __name__ == "__main__":
    unittest.main()
