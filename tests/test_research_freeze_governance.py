import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_stage7a_is_not_active_research_candidate():
    text = (ROOT / "SKY_SYSTEM_REGISTRY_V2_1.md").read_text(encoding="utf-8")
    active = text.split("## Active research candidates", 1)[1].split(
        "## Evidence-only features", 1
    )[0]
    rejected = text.split("## Rejected candidate families", 1)[1].split(
        "## Historical Revenue PIT coverage audit", 1
    )[0]
    assert "Stage 7A Broader Market Alpha" not in active
    assert "Stage 7A Broader Market Alpha" in rejected


def test_freeze_registry_has_single_vnext_lane():
    payload = json.loads(
        (ROOT / "research" / "research_freeze_registry.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["sole_vnext_lane"] == (
        "Residual / Market-Neutral Cross-sectional Ranking"
    )
    assert "P0-S 5m Breakout" in payload["frozen_families"]
    assert "Stage 7A Broader Market Alpha A1-A5" in payload["frozen_families"]


def test_vnext_preregistration_forbids_result_driven_retuning():
    text = (
        ROOT / "research" / "VNEXT_RESIDUAL_RANKING_PREREGISTRATION.md"
    ).read_text(encoding="utf-8")
    assert "PRE-REGISTERED / RESEARCH_ONLY" in text
    assert "Residual3D" in text
    assert "Residual5D" in text
    assert "Residual10D" in text
    assert "No threshold or feature-family change may use Research Test" in text
    assert "LSTM, Transformer, or RL" in text
    assert "Portfolio implementation preserves positive expectancy" in text
