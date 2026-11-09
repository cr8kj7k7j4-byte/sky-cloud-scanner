from datetime import datetime, timezone
from research.sky_recovery_watchdog import audit, FIELDS


def test_nighttime_old_observations_are_historical_only():
    state = {"published_at_utc": "2026-11-09T04:04:00+00:00",
             "reports": {"swing5d_research": {
                 "information_columns_13col": list(FIELDS),
                 "information_count_13col": 1484}}}
    result = audit(state, datetime(2026, 11, 9, 16, 0, tzinfo=timezone.utc))
    assert result["verdict"] == "REPORT_AVAILABLE_HISTORICAL_ONLY"
    assert result["report_fresh_for_market_session"] is False
    assert result["strategy_production_eligible"] is False


def test_market_open_requires_fresh_delivery_and_nonzero_rows():
    state = {"published_at_utc": "2026-11-09T04:04:00+00:00",
             "reports": {"swing5d_research": {
                 "information_columns_13col": list(FIELDS),
                 "information_count_13col": 0}}}
    result = audit(state, datetime(2026, 11, 10, 1, 25, tzinfo=timezone.utc))
    assert result["verdict"] == "BLOCKED_MISSING_OBSERVATIONS"


def test_empty_status_fails_closed():
    assert audit({}, datetime(2026, 11, 10, 0, 45, tzinfo=timezone.utc))["verdict"] == "BLOCKED_NO_13_COLUMNS"
