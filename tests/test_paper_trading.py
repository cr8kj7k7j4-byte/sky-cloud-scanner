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
