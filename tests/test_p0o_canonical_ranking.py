from src.ranking_engine import (
    screening_rank_score,
    rank_screening_candidates,
    transparent_baseline_rank,
)
from src.sky_rules import score_for_ranking


def test_legacy_alias_matches_canonical_screening_score():
    row = {
        "change_pct": 3.2,
        "trade_value": 50_000_000,
        "volume": 12_000,
    }
    assert score_for_ranking(row) == screening_rank_score(row)


def test_screening_ranking_orders_candidates_and_adds_position():
    rows = [
        {"symbol": "A", "change_pct": 1.0, "trade_value": 10_000_000, "volume": 1000},
        {"symbol": "B", "change_pct": 5.0, "trade_value": 50_000_000, "volume": 5000},
    ]
    ranked = rank_screening_candidates(rows)
    assert ranked[0]["symbol"] == "B"
    assert ranked[0]["ranking_position"] == 1
    assert ranked[0]["rank_score"] > ranked[1]["rank_score"]


def test_screening_score_is_not_probability_contract():
    row = {"change_pct": 20, "trade_value": 1_000_000_000, "volume": 100_000}
    score = screening_rank_score(row)
    assert score > 1.0
    # Deliberately not bounded to 0..1 or 0..100: it is an ordering score.
    assert score != max(0.0, min(1.0, score))


def test_research_prediction_remains_nonproduction():
    pred = transparent_baseline_rank({
        "momentum_1": 1.0,
        "momentum_5": 2.0,
        "volume_ratio": 1.4,
    })
    assert pred.production_eligible is False
