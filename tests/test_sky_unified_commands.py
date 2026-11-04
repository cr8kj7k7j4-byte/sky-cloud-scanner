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
