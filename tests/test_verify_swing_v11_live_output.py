from research.verify_swing_v11_live_output import validate_swing_scan_output


def test_real_20261104_stale_signal_fails_closed():
    result = validate_swing_scan_output({
        "signal_date": "2026-10-22",
        "signal_date_guard": {
            "status": "STALE_OR_FUTURE_SIGNAL",
            "fresh": False,
            "expected_signal_date": "2026-11-03",
        },
        "candidate_count": 0,
    })
    assert result["status"] == "BLOCKED_STALE_SIGNAL_HISTORY"
    assert not result["publication_allowed"]


def test_previous_trading_day_signal_passes_but_not_production():
    result = validate_swing_scan_output({
        "signal_date": "2026-11-03",
        "signal_date_guard": {
            "status": "PASS",
            "fresh": True,
            "expected_signal_date": "2026-11-03",
        },
        "candidate_count": 0,
    })
    assert result["status"] == "PASS"
    assert result["production_eligible"] is False
