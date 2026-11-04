"""Prevent retired research workflows and duplicate freeze rows from recurring."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = (
    "w2-baseline-d-false-start-reclaim.yml",
    "w2-false-reclaim-short-baseline-e-backtest-recovery.yml",
    "w2-top100-velocity-baseline.yml",
    "w2-top100-velocity-baseline-a.yml",
    "stage6b-catalyst-backtest.yml",
    "stage6c-interaction-research.yml",
    "stage6d-reaction-first.yml",
    "stage7a-broader-market-alpha.yml",
    "backtest-weak-regime-portfolio.yml",
    "backtest-event-driven-rank-oos.yml",
    "backtest-event-stack-oos.yml",
    "backtest-intraday-rank-oos.yml",
    "backtest-catalyst-event-oos.yml",
)


def test_archived_rejected_replay_workflow_entrypoints_removed():
    workflows = ROOT / ".github" / "workflows"
    assert all(not (workflows / name).exists() for name in FROZEN)


def test_archived_results_and_production_baselines_preserved():
    frozen = (ROOT / "research" / "RESEARCH_FREEZE_REGISTRY.md").read_text()
    registry = (ROOT / "SKY_SYSTEM_REGISTRY_V2_1.md").read_text()
    assert "ARCHIVED_NO_RETUNE" in frozen
    assert "False-Reclaim Short Baseline E" in frozen
    assert "Sky Day Trading v1.4" in registry
    assert "Sky Swing V1.0" in registry
    assert (ROOT / ".github" / "workflows" / "scan.yml").is_file()
    assert (ROOT / ".github" / "workflows" / "research-freeze-governance.yml").is_file()


def test_governance_table_rows_have_no_known_duplicate_fragments():
    frozen = (ROOT / "research" / "RESEARCH_FREEZE_REGISTRY.md").read_text()
    registry = (ROOT / "SKY_SYSTEM_REGISTRY_V2_1.md").read_text()
    assert "|ndidate-universe" not in registry
    assert "|n=9,934" not in frozen
    for text in (frozen, registry):
        assert "| ARCHIVED_NO_RETUNE" in frozen
        assert "Top100" in text
