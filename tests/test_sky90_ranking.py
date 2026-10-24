from src.training_dataset import build_training_dataset
from src.ranking_engine import transparent_baseline_rank, rank_candidates, summarize_ranking
from src.model_registry import baseline_model_card, can_promote


def test_training_dataset_requires_complete_outcome():
    records=[
        {
            "record_id":"a",
            "observed_at":"2026-01-01T09:05:00+08:00",
            "symbol":"2409",
            "features":{"features":{"momentum_1":1.0,"momentum_5":2.0}},
            "outcome":{"status":"COMPLETE","r_multiple":1.2,"mfe_pct":3.0,"mae_pct":-1.0,"hit_target":True,"hit_stop":False},
        },
        {
            "record_id":"b",
            "observed_at":"2026-01-01T09:10:00+08:00",
            "symbol":"3481",
            "features":{"features":{"momentum_1":1.0}},
            "outcome":{},
        },
    ]
    ds=build_training_dataset(records)
    assert ds["eligible_count"]==1
    assert ds["rejected_count"]==1
    assert ds["rows"][0]["targets"]["r_multiple"]==1.2


def test_transparent_baseline_never_production_eligible():
    p=transparent_baseline_rank({"momentum_1":1.0,"momentum_5":2.0,"volume_ratio":1.5,"relative_strength":1.0})
    assert p.production_eligible is False
    assert p.score is not None


def test_rank_candidates_orders_by_score():
    items=[
        {"symbol":"A","features":{"momentum_1":0.1,"momentum_5":0.2}},
        {"symbol":"B","features":{"momentum_1":2.0,"momentum_5":3.0,"volume_ratio":2.0}},
    ]
    ranked=rank_candidates(items)
    assert ranked[0]["symbol"]=="B"
    assert ranked[0]["ranking_position"]==1
    assert summarize_ranking(ranked)["production_eligible"] is False


def test_model_registry_blocks_unvalidated_model():
    card=baseline_model_card()
    gate=can_promote(card)
    assert gate["allowed"] is False
    assert "OOS樣本數不足" in gate["reasons"]
