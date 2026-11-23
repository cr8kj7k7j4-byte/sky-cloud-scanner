from copy import deepcopy

from src.swing_two_track_acceptance import assess


def evidence():
    report = {
        "generated_at": "2026-11-23T12:49:19+08:00",
        "universe_count": 2000,
        "snapshot_coverage_pct": 95.0,
        "snapshot_exchange_counts": {"TWSE": 1000, "TPEx": 900},
        "source_health": {"official_universe": {"twse": 1050, "tpex": 950}},
        "observations_are_trade_signals": False,
        "operational_full_market_scan": False,
        "live_whole_market_certified": False,
        "quote_scope": "PARTIAL_EXECUTED_LIVE",
        "market_data_gate": "BLOCKED_EXTERNAL_DATA_NO_TRADE",
        "snapshot_individual_confirmation": [],
        "unverified_snapshot_observation_count": 1,
    }
    snapshot = {
        "generated_at": "2026-11-23T12:49:19+08:00",
        "source": "Fugle bulk snapshot",
        "observed_symbols": 1,
        "data": [{
            "symbol": "1234", "exchange": "TWSE", "source": "Fugle bulk snapshot",
            "snapshot_date": "2026-11-23",
            "strategy_signal": False, "production_eligible": False,
        }],
    }
    return report, snapshot


def test_snapshot_acceptance_does_not_promote_market_or_trades():
    report, snapshot = evidence()
    out = assess(report, snapshot)
    assert out["snapshot_screen_status"] == "PASS_SNAPSHOT_OBSERVATION_ONLY"
    assert out["full_market_execution_certification_status"] == "HOLD_FULL_MARKET_EXECUTED_TRADE_TIME"
    assert out["candidate_execution_status"] == "HOLD_CANDIDATE_EXECUTION_EVIDENCE"
    assert out["candidate_trade_gate"].startswith("HOLD")
    assert out["production_eligible"] is False
    assert out["automatic_order"] is False
    assert out["trade_action"] == "禁止交易"


def test_stale_or_missing_or_low_coverage_snapshot_fails_closed():
    report, snapshot = evidence()
    for change in ("stale", "missing", "low", "market", "signal", "invalid"):
        r, s = deepcopy(report), deepcopy(snapshot)
        if change == "stale":
            s["data"][0]["snapshot_date"] = "2026-11-22"
        elif change == "missing":
            s["data"] = []
            s["observed_symbols"] = 0
        elif change == "low":
            r["snapshot_coverage_pct"] = 70
        elif change == "market":
            r["snapshot_exchange_counts"]["TPEx"] = 1
        elif change == "signal":
            s["data"][0]["strategy_signal"] = True
        elif change == "invalid":
            s["generated_at"] = "2026-11-23T12:49:19"
        assert assess(r, s)["snapshot_screen_status"] == "HOLD_SNAPSHOT_EVIDENCE"



def test_boolean_official_universe_size_rejected_even_when_coverage_looks_valid():
    # bool is an int subclass; fake True coverage denominators must fail closed.
    report, snapshot = evidence()
    report["source_health"]["official_universe"] = {"twse": True, "tpex": True}
    report["snapshot_exchange_counts"] = {"TWSE": 1, "TPEx": 1}
    out = assess(report, snapshot)
    assert out["snapshot_screen_status"] == "HOLD_SNAPSHOT_EVIDENCE"
    assert out["candidate_trade_gate"].startswith("HOLD")
    assert out["production_eligible"] is False


def test_individual_execution_pass_does_not_enable_trade():
    report, snapshot = evidence()
    report["snapshot_individual_confirmation"] = [{
        "symbol": "1234", "strategy_signal": False, "production_eligible": False,
        "data_status": "FRESH_EXECUTED_TRADE", "verified_executed_price": 52.0,
        "verified_executed_at": "2026-11-23T12:49:00+08:00",
        "individual_checked_at_tpe": "2026-11-23T12:49:19+08:00",
    }]
    out = assess(report, snapshot)
    assert out["candidate_execution_status"] == "PASS_BOUNDED_INDIVIDUAL_EXECUTION_ONLY"
    assert out["full_market_execution_certification_status"].startswith("HOLD")
    assert out["candidate_trade_gate"].startswith("HOLD")
    assert out["production_eligible"] is False


def test_fake_market_gate_flag_does_not_pass():
    report, snapshot = evidence()
    report["operational_full_market_scan"] = True
    report["live_whole_market_certified"] = True
    report["quote_scope"] = "WHOLE_MARKET_EXECUTED_LIVE"
    assert assess(report, snapshot)["full_market_execution_certification_status"].startswith("HOLD")


def test_workflow_uses_two_tracks_without_replacing_original_guard():
    from pathlib import Path
    yml = Path(".github/workflows/swing-live-scan.yml").read_text(encoding="utf-8")
    assert "from src.swing_two_track_acceptance import assess" in yml
    assert "independently_recomputed = assess(report, snapshot)" in yml
    assert "two_track != independently_recomputed" in yml
    assert "TWO_TRACK_SAME_RUN_INDEPENDENT_RECOMPUTATION_MISMATCH" in yml
    assert "PASS_SNAPSHOT_OBSERVATION_ONLY" in yml
    assert "snapshot_screen_status" in yml
    assert "candidate_execution_status" in yml
    assert "full_market_execution_certification_status" in yml
    module = Path("src/swing_two_track_acceptance.py").read_text(encoding="utf-8")
    # The canonical certification criteria are in the independent evaluator,
    # not duplicated as a literal in the workflow orchestration.
    assert "PASS_OPERATIONAL_WHOLE_MARKET_LIVE_RESEARCH_ONLY" in module
    assert "HOLD_FULL_STRATEGY_AND_RISK_NOT_VERIFIED" in module
    assert "sky-fugle-paid-global-research-v1-live-wholemarket" in yml


def test_snapshot_detail_integrity_and_capture_cutoff_fail_closed():
    report, snapshot = evidence()
    assert assess(report, snapshot)["snapshot_screen_status"] == "PASS_SNAPSHOT_OBSERVATION_ONLY"
    for change in ("wrong_report_count", "wrong_file_count", "duplicate", "wrong_market",
                   "different_day", "late_capture", "future_capture", "near_future_capture", "missing_symbol"):
        r, s = deepcopy(report), deepcopy(snapshot)
        if change == "wrong_report_count":
            r["unverified_snapshot_observation_count"] = 2
        elif change == "wrong_file_count":
            s["observed_symbols"] = 2
        elif change == "duplicate":
            s["data"].append(deepcopy(s["data"][0]))
            s["observed_symbols"] = 2
            r["unverified_snapshot_observation_count"] = 2
        elif change == "wrong_market":
            s["data"][0]["exchange"] = "UNKNOWN"
        elif change == "different_day":
            s["generated_at"] = "2026-11-22T12:49:19+08:00"
        elif change == "late_capture":
            s["generated_at"] = "2026-11-23T12:45:00+08:00"
        elif change == "future_capture":
            s["generated_at"] = "2026-11-23T12:53:30+08:00"
        elif change == "near_future_capture":
            # Even a one-second post-report snapshot violates point-in-time causality.
            s["generated_at"] = "2026-11-23T12:49:20+08:00"
        elif change == "missing_symbol":
            s["data"][0]["symbol"] = ""
        assert assess(r, s)["snapshot_screen_status"] == "HOLD_SNAPSHOT_EVIDENCE"
        assert assess(r, s)["production_eligible"] is False


def test_individual_checked_at_fails_closed():
    """A2 uses the actual bounded quote check, never just a report-level timestamp."""
    for checked, traded in (
        (None, "2026-11-23T12:49:00+08:00"),
        ("2026-11-23T12:49:19", "2026-11-23T12:49:00+08:00"),
        ("2026-11-23T12:49:19+08:00", "2026-11-23T12:49:30+08:00"),
        ("2026-11-23T12:53:01+08:00", "2026-11-23T12:49:00+08:00"),
        ("2026-11-23T12:59:20+08:00", "2026-11-23T12:59:00+08:00"),
        ("2026-11-24T09:00:00+08:00", "2026-11-24T08:59:59+08:00"),
    ):
        report, snapshot = evidence()
        report["snapshot_individual_confirmation"] = [{
            "symbol": "1234", "strategy_signal": False, "production_eligible": False,
            "data_status": "FRESH_EXECUTED_TRADE", "verified_executed_price": 52.0,
            "verified_executed_at": traded, "individual_checked_at_tpe": checked,
        }]
        out = assess(report, snapshot)
        assert out["candidate_execution_status"] == "HOLD_CANDIDATE_EXECUTION_EVIDENCE"
        assert out["candidate_trade_gate"].startswith("HOLD")
        assert out["automatic_order"] is False
