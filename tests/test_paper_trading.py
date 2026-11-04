import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.paper_trading import (
    evaluate_paper_gate,
    build_paper_snapshot,
    write_paper_run_file,
)


def test_shadow_never_simulates():
    g = evaluate_paper_gate("shadow", "PASS_TO_PAPER_TRADING")
    assert g.enabled is True
    assert g.simulation_allowed is False


def test_paper_requires_oos_pass():
    g = evaluate_paper_gate("paper", "RESEARCH_ONLY")
    assert g.simulation_allowed is False


def test_paper_allows_only_after_oos_pass():
    g = evaluate_paper_gate("paper", "PASS_TO_PAPER_TRADING")
    assert g.simulation_allowed is True


def test_snapshot_keeps_strategy_research_flag():
    gate = evaluate_paper_gate("shadow", "RESEARCH_ONLY")
    snap = build_paper_snapshot(
        run_id="r1",
        observed_at="2026-10-25T09:05:00+08:00",
        item={
            "symbol": "2409",
            "name": "友達",
            "last": 10.2,
            "strategy_plan": {
                "setup": "5分K平台突破候選",
                "trigger": 10.2,
                "max_entry": 10.25,
                "stop": 10.0,
                "target": 10.6,
                "rr": 2.0,
                "production_eligible": False,
            },
            "risk": {"status": "ALLOW"},
            "monitor": {"state": "TRIGGERED"},
        },
        gate=gate,
    )
    assert snap["strategy"]["production_eligible"] is False
    assert snap["action"] == "SHADOW_OBSERVE"


def test_write_paper_file(tmp_path):
    p = write_paper_run_file(tmp_path / "paper.json", [{"symbol": "2409"}])
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["records"][0]["symbol"] == "2409"


def test_snapshot_preserves_forward_version_lineage():
    gate = evaluate_paper_gate("shadow", "RESEARCH_ONLY")
    snap = build_paper_snapshot(
        run_id="r2",
        observed_at="2026-10-27T09:05:00+08:00",
        item={
            "symbol":"2330",
            "strategy_id":"Sky Day Trading",
            "strategy_version":"v1.4 Dynamic Capital Rotation / P0-C MVP",
            "system_version":"Sky V2.1",
            "scanner_version":"0.5",
            "historical_full_rule_replay_status":"HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE",
            "risk":{"status":"RISK_INPUT_REQUIRED"},
            "monitor":{"state":"OBSERVE"},
        },
        gate=gate,
    )
    assert snap["strategy_id"]=="Sky Day Trading"
    assert snap["strategy_version"]=="v1.4 Dynamic Capital Rotation / P0-C MVP"
    assert snap["system_version"]=="Sky V2.1"
    assert snap["scanner_version"]=="0.5"
    assert (
        snap["historical_full_rule_replay_status"]
        =="HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE"
    )
    assert snap["research_context"]["scanner_version"]=="0.5"


def test_paper_snapshot_preserves_gainer_rank_context():
    from src.paper_trading import PaperTradingGate, build_paper_snapshot

    gate = PaperTradingGate(
        mode="shadow",
        oos_verdict="RESEARCH_ONLY",
        enabled=True,
        simulation_allowed=False,
        reason="test",
    )
    item = {
        "symbol": "1234",
        "name": "Test",
        "gainer_rank": 37,
        "top100_gainer_member": True,
        "gainer_universe_size": 1980,
        "gainer_rank_source": "current_snapshot_change_pct",
    }
    snap = build_paper_snapshot(
        run_id="r1",
        observed_at="2026-10-26T09:30:00+08:00",
        item=item,
        gate=gate,
    )
    assert snap["gainer_rank"] == 37
    assert snap["top100_gainer_member"] is True
    assert snap["gainer_universe_size"] == 1980
    assert snap["gainer_rank_source"] == "current_snapshot_change_pct"
    assert snap["research_context"]["gainer_rank"] == 37
    assert snap["research_context"]["top100_gainer_member"] is True


def test_paper_snapshot_receives_canonical_observation_id_but_no_trade_authorization():
    from src.trade_logger import build_trade_decision_record
    from datetime import datetime
    gate = evaluate_paper_gate("shadow", "RESEARCH_ONLY")
    observed = "2026-11-04T09:05:00+08:00"
    item = {"symbol": "2330", "strategy_version": "v1.4", "risk": {"status": "BLOCK"}}
    snap = build_paper_snapshot(run_id="run-1", observed_at=observed, item=item, gate=gate)
    canonical = build_trade_decision_record(
        item=item, run_id="run-1", observed_at=datetime.fromisoformat(observed),
        mode="SHADOW_OBSERVATION",
    )
    assert snap["record_id"] == canonical.record_id
    assert snap["observation_record_id"] == canonical.record_id
    assert snap["decision_id"] is None
    assert snap["decision_provenance_status"] == "RANKING_OBSERVATION_ONLY"
    assert snap["action"] == "SHADOW_OBSERVE"
    assert build_paper_snapshot(run_id="run-1", observed_at=observed, item=item, gate=gate)["record_id"] == canonical.record_id


def test_paper_observation_id_changes_with_run_or_symbol():
    gate = evaluate_paper_gate("shadow", "RESEARCH_ONLY")
    obs = "2026-11-04T09:05:00+08:00"
    a = build_paper_snapshot(run_id="one", observed_at=obs, item={"symbol": "2330"}, gate=gate)
    b = build_paper_snapshot(run_id="two", observed_at=obs, item={"symbol": "2330"}, gate=gate)
    c = build_paper_snapshot(run_id="one", observed_at=obs, item={"symbol": "2317"}, gate=gate)
    assert len({a["record_id"], b["record_id"], c["record_id"]}) == 3
