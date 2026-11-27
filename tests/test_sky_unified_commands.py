from src.sky_command_router import route_command
from src.sky_unified_commands import REGISTRIES


def test_unified_market_route():
    route = route_command("Sky 全市場掃描")
    assert route.command_family == "SKY_UNIFIED_MARKET_SCAN"
    assert route.whole_market_required is True
    assert route.realtime_required is True
    assert "sky-unified-commands.yml" in route.execution_target


def test_unified_health_route():
    route = route_command("Sky 系統健康檢查")
    assert route.command_family == "SKY_UNIFIED_SYSTEM_HEALTH"
    assert route.realtime_required is False


def test_unified_validation_route():
    route = route_command("Sky 全模型驗證")
    assert route.command_family == "SKY_UNIFIED_MODEL_VALIDATION"
    assert route.data_mode == "GOVERNED_RESEARCH_EVIDENCE"


def test_required_registries_are_present():
    from pathlib import Path
    assert len(REGISTRIES) == 3
    assert all(Path(p).exists() for p in REGISTRIES)



def test_operational_coverage_gate_fails_closed():
    from src.sky_unified_commands import operational_market_evidence_ok
    assert not operational_market_evidence_ok({"available": True, "operational_full_market_scan": False, "quote_coverage_pct": 4.03})
    assert not operational_market_evidence_ok({"available": True, "operational_full_market_scan": True, "quote_coverage_pct": 7.3})
    assert not operational_market_evidence_ok({"available": False, "operational_full_market_scan": True, "quote_coverage_pct": 95.0})
    assert not operational_market_evidence_ok({"available": True, "operational_full_market_scan": True, "quote_coverage_pct": None})
    # A broad daily signal universe or MIS operational count is not a
    # certified whole-market executed-live quote set.
    assert not operational_market_evidence_ok({"available": True, "operational_full_market_scan": True, "quote_coverage_pct": 85.0})
    assert not operational_market_evidence_ok({
        "available": True, "operational_full_market_scan": True,
        "quote_coverage_pct": 85.0, "quote_scope": "CANDIDATES_ONLY",
        "live_whole_market_certified": True,
    })
    assert operational_market_evidence_ok({
        "available": True, "operational_full_market_scan": True,
        "quote_coverage_pct": 85.0, "quote_scope": "WHOLE_MARKET_EXECUTED_LIVE",
        "live_whole_market_certified": True,
    })


def test_source_health_never_conflates_api_access_with_market_certification():
    from src.sky_unified_commands import source_health_verdict
    source = {
        "time": "2026-11-04T10:39:00+08:00",
        "official_universe": {"twse": 1000, "tpex": 900},
        "universe_count": 1900,
        "mis_sample": {"requested": 120, "returned": 8},
        "fugle_snapshot_TSE": {"ok": False, "status": "plan_restricted"},
        "fugle_quote_2330": {"ok": True, "status": "FRESH_EXECUTED_TRADE",
                              "fresh_executed_trade": True},
    }
    result = source_health_verdict(source, {"generated_at_utc": "2026-11-04T12:00:00Z",
                                             "workflows": [{"path": "scan.yml",
                                                            "verdict": "ATTENTION"}]})
    assert result["all_checks_passed"] is False
    assert result["fugle"]["fugle_snapshot_TSE"]["status"] == "plan_restricted"
    assert result["schedule"]["attention"][0]["path"] == "scan.yml"
    assert result["mis_sample"]["returned"] == 8


def test_validation_only_reads_existing_provenance(monkeypatch, tmp_path):
    from src import sky_unified_commands as u
    import json
    monkeypatch.chdir(tmp_path)
    for p in u.REGISTRIES:
        from pathlib import Path
        path = Path(p)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("baseline", encoding="utf-8")
    p = tmp_path / "docs/SKY_EXTERNAL_LATEST_STATUS.json"
    p.write_text(json.dumps({"generated_at_utc": "2026-11-04T01:00:00Z",
                            "w4_dashboard": {
                                "sample_sufficiency": {
                                    "sufficient": False,
                                    "observed": {"samples": 100, "trading_days": 5}},
                                "strategy_evidence_integrity": {
                                    "eligible_strategy_records": 0, "status": "INSUFFICIENT_DATA"},
                                "forward_trade_provenance": {
                                    "status": "PRODUCTION_DECISION_PROVENANCE_BLOCKED"}}}),
                 encoding="utf-8")
    monkeypatch.setattr(u, "execute", lambda command: {"exit_code": 0})
    result = u.validation_mode()
    assert result["decision"] == "VALIDATION_INSUFFICIENT_DATA_NO_PROMOTION"
    assert result["evidence"]["sample_count"] == 100
    assert result["evidence"]["after_cost_expectancy_r"] is None
    assert result["evidence"]["production_eligible"] is False


def test_live_market_guard_taiwan_hours():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from src.sky_unified_commands import market_session_open
    tz = ZoneInfo("Asia/Taipei")
    assert not market_session_open(datetime(2026, 11, 4, 8, 59, tzinfo=tz))
    assert market_session_open(datetime(2026, 11, 4, 9, 5, tzinfo=tz))
    assert market_session_open(datetime(2026, 11, 4, 13, 29, tzinfo=tz))
    assert not market_session_open(datetime(2026, 11, 4, 13, 30, tzinfo=tz))
    assert not market_session_open(datetime(2026, 11, 7, 10, 0, tzinfo=tz))


def test_model_validation_comment_bridge_is_owner_only_and_no_paid_scan():
    """Prevent arbitrary issue comments from dispatching research checks."""
    from pathlib import Path

    raw = Path(".github/workflows/sky-unified-commands.yml").read_text(encoding="utf-8")
    assert "issue_comment:" in raw
    assert "types: [created]" in raw
    guard = raw.split("    if: >-", 1)[1].split("    runs-on:", 1)[0]
    assert "github.event.issue.number == 363" in guard
    assert "github.event.comment.user.login == github.repository_owner" in guard
    assert "github.event.comment.author_association == 'OWNER'" in guard
    assert "github.event.comment.body == 'Sky 全模型驗證'" in guard
    assert 'COMMAND="model_validation"' in raw
    assert '"request_id": ("issue-comment-" + os.environ["ISSUE_COMMENT_ID"]' in raw
    assert 'command = ("model_validation" if os.environ.get("EVENT_NAME") == "issue_comment"' in raw
    assert not any(line.startswith("  schedule:") for line in raw.splitlines())  # Paused schedule stays paused.


def test_unified_market_report_exposes_swing_research_even_when_trade_gate_fails(monkeypatch, tmp_path):
    """Snapshot observations are visible without conferring trading eligibility."""
    import json
    from pathlib import Path
    from src import sky_unified_commands as u
    monkeypatch.chdir(tmp_path)

    def execute_stub(command):
        if "trading_calendar" in " ".join(command):
            (tmp_path / "output/sky_unified").mkdir(parents=True, exist_ok=True)
            (tmp_path / "output/sky_unified/calendar.json").write_text(
                json.dumps({"source_status": "PASS", "should_scan": True}), encoding="utf-8")
            return {"exit_code": 0}
        return {"exit_code": 0}

    monkeypatch.setattr(u, "market_session_open", lambda: True)
    monkeypatch.setattr(u, "execute", execute_stub)
    monkeypatch.setattr(u, "BASE", tmp_path / "output/sky_unified")
    monkeypatch.setattr(u, "operational_market_evidence_ok", lambda _: False)
    swing = tmp_path / "output/swing_live/latest_swing.json"
    swing.parent.mkdir(parents=True, exist_ok=True)
    swing.write_text(json.dumps({
        "generated_at": "2026-11-27T12:30:00+08:00",
        "analysis_mode": "OBSERVATION_ONLY",
        "analysis_observation_count": 2,
        "analysis_observation_preview": [
            {"symbol": "1234", "indicative_last_price": 40.0,
             "snapshot_date": "2026-11-27",
             "data_status": "UNVERIFIED_EXECUTED_TRADE_TIME"},
            {"symbol": "5678", "indicative_last_price": 150.0,
             "snapshot_date": "2026-11-27",
             "data_status": "UNVERIFIED_EXECUTED_TRADE_TIME"},
        ],
        "candidate_count": 0,
        "market_data_gate": "BLOCKED_EXTERNAL_DATA_NO_TRADE",
        "live_whole_market_certified": False,
        "quote_scope": "BULK_SNAPSHOT_INDICATIVE_ONLY",
        "deep_candidates": [],
    }), encoding="utf-8")
    result = u.market_mode()
    item = result["research_observations"]["swing_research"]
    assert item["available"] is True
    assert item["count"] == 2
    assert [x["symbol"] for x in item["preview"]] == ["1234", "5678"]
    assert item["real_time_trade_eligible"] is False
    assert result["reports"]["swing_research"]["candidate_count"] == 0
    assert result["decision"] == "DATA_COVERAGE_INSUFFICIENT_NO_TRADE"
