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
