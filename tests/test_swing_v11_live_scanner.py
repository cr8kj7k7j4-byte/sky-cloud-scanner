from datetime import datetime
from zoneinfo import ZoneInfo

from src.swing_v11_live_scanner import frozen_signal_pass, _entry_status

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


def test_intraday_does_not_rewrite_open_entry_rule():
    code, _ = _entry_status(datetime(2026, 10, 27, 10, 11, tzinfo=TZ))
    assert code == "OPEN_ENTRY_PASSED_NO_CHASE"
