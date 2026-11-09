"""Daytrade pre-open checks must not conflate paid API access with fresh trades."""
from datetime import datetime
from zoneinfo import ZoneInfo
from research.sky_daytrade_preopen_readiness import evaluate


def fixture():
    return {
        "mis_sample": {"status": "SKIPPED_FUGLE_ONLY", "requested": 0},
        "fugle_snapshot_TSE": {"ok": True, "count": 1060, "date": "2026-11-09"},
        "fugle_snapshot_OTC": {"ok": True, "count": 895, "date": "2026-11-09"},
        "fugle_quote_2330": {"api_accessible": True, "fresh_executed_trade": False},
        "fugle_quote_8089_otc": {"api_accessible": True, "fresh_executed_trade": False},
    }


def test_paid_api_preopen_pass_never_approves_trades():
    x = evaluate(fixture(), now=datetime(2026, 11, 10, 8, 40, tzinfo=ZoneInfo("Asia/Taipei")))
    assert x["api_readiness"] == "PASS"
    assert x["execution_freshness"] == "NOT_TESTABLE_PREOPEN"
    assert x["production_trade_eligible"] is False
    assert x["strategy_levels"] == "NOT_VERIFIED"
    assert x["provider_data_dates"]["TSE"] == "2026-11-09"


def test_mis_request_is_blocked():
    d = fixture()
    d["mis_sample"]["requested"] = 20
    assert evaluate(d)["api_readiness"] == "BLOCKED"


def test_missing_otc_paid_permission_is_blocked():
    d = fixture()
    d["fugle_snapshot_OTC"]["ok"] = False
    assert evaluate(d)["api_readiness"] == "BLOCKED"


def test_missing_individual_quote_is_blocked():
    d = fixture()
    d["fugle_quote_8089_otc"] = {"api_accessible": False}
    assert evaluate(d)["api_readiness"] == "BLOCKED"


def test_preopen_workflow_rechecks_previous_real_scan_and_never_sets_trade_approval():
    from pathlib import Path
    workflow = Path(".github/workflows/sky-daytrade-preopen-readiness.yml").read_text(encoding="utf-8")
    assert "15,30,45,55 0 * * 1-5" in workflow
    assert "actions: read" in workflow
    assert "gh run download" in workflow
    assert "research.verify_13col_artifact" in workflow
    assert "FUGLE_API_KEY:" in workflow
    assert "ALLOW_MIS_OTC_FALLBACK: \"0\"" in workflow
    assert "SKY_FUGLE_ONLY_MARKETDATA: \"1\"" in workflow


def test_preopen_bounded_retry_and_evidence_preserved():
    from pathlib import Path
    yml = Path(".github/workflows/sky-daytrade-preopen-readiness.yml").read_text(encoding="utf-8")
    assert "for attempt in 1 2 3" in yml
    assert yml.count("for attempt in 1 2 3") == 3
    assert "preopen_retry_attempts.log" in yml
    assert "sleep 10" in yml
    assert "test \"$ok\" -eq 1" in yml
    assert "rm -rf previous-scan" in yml
    assert "research.verify_13col_artifact" in yml
    assert "15,30,45,55 0 * * 1-5" in yml
    assert "SKY_FUGLE_ONLY_MARKETDATA: \"1\"" in yml
