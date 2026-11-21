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


def test_pass_guard_with_inconsistent_dates_is_blocked():
    result = validate_swing_scan_output({
        "signal_date": "2026-11-02",
        "signal_date_guard": {"status": "PASS", "fresh": True, "expected_signal_date": "2026-11-03"},
    })
    assert result["status"] == "BLOCKED_STALE_SIGNAL_HISTORY"
    assert not result["publication_allowed"]

def test_missing_malformed_output_fails_closed_and_writes_receipt(tmp_path):
    import json
    import subprocess
    import sys
    for raw in (None, "not-json", "[]", "null"):
        target = tmp_path / "scan.json"
        receipt = tmp_path / "freshness_gate.json"
        if raw is not None:
            target.write_text(raw, encoding="utf-8")
        elif target.exists():
            target.unlink()
        cp = subprocess.run(
            [sys.executable, "-m", "research.verify_swing_v11_live_output",
             "--input", str(target), "--report", str(receipt)],
            capture_output=True, text=True, check=False)
        assert cp.returncode != 0
        result = json.loads(receipt.read_text(encoding="utf-8"))
        assert result["status"] == "BLOCKED_SCAN_OUTPUT_MISSING"
        assert result["publication_allowed"] is False
        assert result["production_eligible"] is False
