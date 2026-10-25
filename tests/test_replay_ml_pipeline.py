import json
from datetime import datetime, timedelta
from pathlib import Path

from src.historical_replay import ReplayPolicy, replay_universe
from src.training_dataset import build_training_dataset
from src.walk_forward import generate_walk_forward_folds
from src.walk_forward_eval import evaluate_walk_forward


def _obj(symbol, scale=1.0):
    data=[]
    base_day=datetime(2026,1,1,9,0)
    for d in range(35):
        start=base_day+timedelta(days=d)
        base=(10.0+d*0.01)*scale
        for i in range(20):
            dt=start+timedelta(minutes=5*i)
            close=base+0.01*i
            data.append({
                "date":dt.isoformat(),
                "open":close-0.01,
                "high":close+0.05,
                "low":close-0.05,
                "close":close,
                "volume":100+i,
                "average":base+0.005*i,
            })
    return {"symbol":symbol,"exchange":"TWSE","data":data}


def test_replay_to_ml_pipeline_contract():
    replay=replay_universe(
        [_obj("A"),_obj("B",1.01)],
        policy=ReplayPolicy(min_history_bars=2,horizon_bars=3),
    )
    ds=build_training_dataset(replay["rows"])
    assert replay["count"] > 0
    assert ds["eligible_count"] > 0

    folds=generate_walk_forward_folds(
        "2026-01-01","2026-02-15",
        train_days=12,validate_days=6,test_days=6,step_days=6,
    )
    report=evaluate_walk_forward(
        ds["rows"],folds,ds["feature_keys"],target_key="r_multiple"
    )
    assert report["production_eligible"] is False
    assert isinstance(report["aggregate"],dict)
