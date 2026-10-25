import json
from pathlib import Path

from research import audit_residual_return_labels as labels
from research import audit_market_residual_spread as baseline


ROOT = Path(__file__).resolve().parents[1]


def test_vnext_horizons_are_frozen():
    assert labels.HORIZONS == [3, 5, 10]
    assert baseline.HORIZONS == [3, 5, 10]


def test_vnext_costs_and_topn_are_frozen():
    assert baseline.COSTS == [0.45, 0.65]
    assert baseline.TOPNS == [3, 5, 10]


def test_vnext_feature_set_matches_preregistration():
    expected = {
        "trend_ma20",
        "trend_ma60",
        "vol20",
        "drawdown20",
        "ret20_rank",
        "market_breadth20",
    }
    assert set(labels.FEATURES) == expected
    assert set(baseline.FEATURES) == expected


def test_vnext_train_only_direction_selection():
    rows = [
        {"f": 1.0, "market_resid_3d": -1.0},
        {"f": 2.0, "market_resid_3d": 0.0},
        {"f": 3.0, "market_resid_3d": 1.0},
    ]
    old = baseline.FEATURES[:]
    try:
        baseline.FEATURES[:] = ["f"]
        selected = baseline.fit_train_directions(rows, 3)
    finally:
        baseline.FEATURES[:] = old
    assert len(selected) == 1
    assert selected[0]["feature"] == "f"
    assert selected[0]["direction"] == 1


def test_vnext_scoring_uses_equal_weight_direction_adjusted_percentiles():
    rows = [
        {"symbol": "A", "date": "2024-01-02", "x": 1.0, "y": 3.0},
        {"symbol": "B", "date": "2024-01-02", "x": 2.0, "y": 2.0},
        {"symbol": "C", "date": "2024-01-02", "x": 3.0, "y": 1.0},
    ]
    selected = [
        {"feature": "x", "direction": 1, "train_rank_ic": 0.1},
        {"feature": "y", "direction": -1, "train_rank_ic": -0.1},
    ]
    scored = baseline.score_rows(rows, selected)
    by_symbol = {r["symbol"]: r["vnext_score"] for r in scored}
    assert by_symbol["C"] > by_symbol["B"] > by_symbol["A"]


def test_preregistration_explicitly_blocks_fresh_oos_claim_for_2026():
    text = (
        ROOT / "research" / "VNEXT_RESIDUAL_RANKING_PREREGISTRATION.md"
    ).read_text(encoding="utf-8")
    assert "Research Test = 2026" in text
    assert "not fresh untouched OOS" in text


def test_industry_residual_is_disabled_until_pit_sector_mapping():
    script = (
        ROOT / "research" / "audit_residual_return_labels.py"
    ).read_text(encoding="utf-8")
    assert "industry_resid_" not in script
    prereg = (
        ROOT / "research" / "VNEXT_RESIDUAL_RANKING_PREREGISTRATION.md"
    ).read_text(encoding="utf-8")
    assert "disabled until historical point-in-time sector" in prereg


def test_no_result_based_winner_selection_in_baseline_v1():
    script = (
        ROOT / "research" / "audit_market_residual_spread.py"
    ).read_text(encoding="utf-8")
    assert "Winner selection: disabled in baseline v1" in script
    assert '"production_eligible":False' in script
    assert '"fresh_oos":False' in script
