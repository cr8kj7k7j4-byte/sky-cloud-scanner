from datetime import datetime
from zoneinfo import ZoneInfo

from src.swing_v11_live_scanner import frozen_signal_pass, _entry_status, intraday_execution_decision, fetch_candidate_live_quotes

TZ = ZoneInfo("Asia/Taipei")


def _base():
    return {
        "breadth": 0.60,
        "close": 50.0,
        "ma20": 48.0,
        "ma60": 45.0,
        "rs_pct": 0.80,
        "prior20_high": 49.0,
        "range_pct": 0.04,
    }


def test_frozen_v11_signal_passes_exact_gates():
    ok, reasons = frozen_signal_pass(_base())
    assert ok is True
    assert reasons == []


def test_frozen_v11_rejects_antichase():
    row = _base()
    row["close"] = 55.0
    row["ma20"] = 50.0
    ok, reasons = frozen_signal_pass(row)
    assert ok is False
    assert any("Anti-Chase" in x for x in reasons)


def test_intraday_session_remains_open_for_execution_overlay():
    code, _ = _entry_status(datetime(2026, 10, 27, 10, 11, tzinfo=TZ))
    assert code == "INTRADAY_EXECUTION_WINDOW"


def test_intraday_overlay_buy_only_at_or_below_open_reference():
    status, action, _ = intraday_execution_decision(49.8, 50.0, 47.0, 59.0)
    assert status == "BUY_ELIGIBLE"
    assert action == "買進"


def test_intraday_overlay_waits_above_open_reference():
    status, action, _ = intraday_execution_decision(50.5, 50.0, 47.0, 59.0)
    assert status == "WAIT_PULLBACK"
    assert action == "等待"


def test_intraday_overlay_rejects_after_stop_failure():
    status, action, _ = intraday_execution_decision(46.9, 50.0, 47.0, 59.0)
    assert status == "REJECT_STOPPED"
    assert action == "禁止交易"


def test_intraday_overlay_rejects_after_target_passed():
    status, action, _ = intraday_execution_decision(59.1, 50.0, 47.0, 59.0)
    assert status == "REJECT_TARGET_PASSED"
    assert action == "禁止交易"


def test_candidate_live_quotes_short_circuits_when_no_frozen_candidates():
    quotes, warnings, meta = fetch_candidate_live_quotes([], [])
    assert quotes == {}
    assert warnings == []
    assert meta == {"requested": 0, "mis": 0, "fugle": 0, "missing": 0}
