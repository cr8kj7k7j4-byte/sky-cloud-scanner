"""Unified all-market workflow must not report success on incomplete quote coverage."""
import json

import src.sky_unified_commands as unified


def _run_with_reports(tmp_path, monkeypatch, *, coverage, exit_code=0):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(unified, "BASE", tmp_path / "output" / "unified")
    unified.BASE.mkdir(parents=True)
    for name in ("latest.json", "swing_live/latest_swing.json", "swing_live/latest_swing5d.json"):
        f = tmp_path / "output" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({
            "operational_full_market_scan": coverage,
            "quote_coverage_pct": 5.39 if not coverage else 95,
            "candidate_count": 0,
            "deep_candidates": [],
        }), encoding="utf-8")

    def stub(argv):
        if "src.trading_calendar" in argv:
            (unified.BASE / "calendar.json").write_text(
                json.dumps({"source_status": "PASS", "should_scan": True}),
                encoding="utf-8",
            )
            return {"exit_code": 0}
        return {"exit_code": exit_code}

    monkeypatch.setattr(unified, "execute", stub)
    return unified.market_mode()


def test_incomplete_coverage_fails_closed(tmp_path, monkeypatch):
    result = _run_with_reports(tmp_path, monkeypatch, coverage=False)
    assert result["decision"] == "INCOMPLETE_FULL_MARKET_COVERAGE_NO_TRADE"


def test_complete_coverage_still_does_not_certify_a_plus(tmp_path, monkeypatch):
    result = _run_with_reports(tmp_path, monkeypatch, coverage=True)
    assert result["decision"] == "PARTIAL_UNVERIFIED_NO_A_PLUS"


def test_runner_failure_takes_priority(tmp_path, monkeypatch):
    result = _run_with_reports(tmp_path, monkeypatch, coverage=True, exit_code=1)
    assert result["decision"] == "SCAN_FAILURE_NO_TRADE"
