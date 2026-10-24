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
