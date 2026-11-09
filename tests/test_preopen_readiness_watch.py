import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from ops.preopen_readiness_watch import evaluate, is_tuesday_run

TPE = ZoneInfo("Asia/Taipei")


def sample(event="schedule", conclusion="failure", status="completed", date="2026-11-10T00:15:00Z"):
    return {"id": 123, "event": event, "status": status, "conclusion": conclusion,
            "head_branch": "main", "created_at": date, "html_url": "https://example.test"}


class PreopenWatchTests(unittest.TestCase):
    def test_not_retried_before_0820(self):
        x = evaluate(datetime(2026, 11, 10, 8, 10, tzinfo=TPE), lambda _: [])
        self.assertEqual("NOT_ELIGIBLE", x["retry"])

    def test_only_once_after_failed_scheduled_run(self):
        x = evaluate(datetime(2026, 11, 10, 8, 20, tzinfo=TPE), lambda _: [sample()])
        self.assertEqual("ONE_RETRY_PERMITTED", x["retry"])

    def test_no_duplicate_if_dispatched(self):
        x = evaluate(datetime(2026, 11, 10, 8, 40, tzinfo=TPE),
                     lambda _: [sample(event="workflow_dispatch")])
        self.assertEqual("NO_RETRY_ALREADY_DISPATCHED", x["retry"])

    def test_in_progress_not_retried(self):
        x = evaluate(datetime(2026, 11, 10, 8, 40, tzinfo=TPE),
                     lambda _: [sample(status="in_progress", conclusion=None)])
        self.assertEqual("NO_RETRY_IN_PROGRESS", x["retry"])

    def test_after_deadline_expired(self):
        x = evaluate(datetime(2026, 11, 10, 9, 51, tzinfo=TPE), lambda _: [])
        self.assertEqual("EXPIRED", x["status"])

    def test_utc_to_taipei(self):
        self.assertTrue(is_tuesday_run(sample()))
        self.assertFalse(is_tuesday_run(sample(date="2026-11-09T05:53:00Z")))


if __name__ == "__main__":
    unittest.main()
