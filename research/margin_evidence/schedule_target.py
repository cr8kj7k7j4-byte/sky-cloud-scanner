"""Resolve the report date for the 23:30 Asia/Taipei scheduled collector.

Scheduled GitHub Actions may start after midnight. Never silently collect a
different day's data. The actual source report dates are validated separately.
"""
from __future__ import annotations
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")
SCHEDULE_LOCAL = time(23, 30)


def scheduled_report_date(started_at: datetime):
    if started_at.tzinfo is None:
        raise ValueError("An aware timestamp is required")
    local = started_at.astimezone(TAIPEI)
    # The 23:30 cron may be queued across local midnight. Prior to 23:30
    # the latest intended session was the previous calendar date.
    if local.time() < SCHEDULE_LOCAL:
        return (local.date() - timedelta(days=1))
    return local.date()


if __name__ == "__main__":
    print(scheduled_report_date(datetime.now(TAIPEI)).isoformat())
