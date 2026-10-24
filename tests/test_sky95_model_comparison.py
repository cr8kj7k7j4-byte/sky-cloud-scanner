from src.model_training import evaluate_predictions, train_and_evaluate
from src.walk_forward_eval import evaluate_walk_forward
from src.walk_forward import generate_walk_forward_folds


def test_regression_metrics_are_trade_aware():
    m=evaluate_predictions([1.0,-0.5,2.0], [0.8,-0.2,1.5]).to_dict()
    assert m["n"]==3
    assert m["expectancy_r"] > 0
    assert m["pf"] > 1
    assert m["max_drawdown_r"] <= 0


def test_training_blocks_small_samples_before_model_fit():
    features=["momentum_1"]
    train=[{"record_id":str(i),"features":{"momentum_1":float(i)},"targets":{"r_multiple":1.0}} for i in range(5)]
    test=[{"record_id":"t","features":{"momentum_1":1.0},"targets":{"r_multiple":1.0}}]
    result=train_and_evaluate(train,test,features)
    assert result["production_eligible"] is False
    for model in result["results"].values():
        assert model["production_eligible"] is False
        assert model["status"] in {"INSUFFICIENT_SAMPLE","DEPENDENCY_UNAVAILABLE"}


def test_walk_forward_report_never_auto_promotes():
    rows=[]
    for i in range(120):
        day=(i%28)+1
        month=(i//28)+1
        rows.append({
            "record_id":str(i),
            "observed_at":f"2026-{month:02d}-{day:02d}T09:15:00+08:00",
            "features":{"momentum_1":float(i%5),"momentum_5":float(i%7)},
            "targets":{"r_multiple":1.0 if i%3 else -0.5},
        })
    folds=generate_walk_forward_folds("2026-01-01","2026-05-30",train_days=50,validate_days=20,test_days=20,step_days=20)
    report=evaluate_walk_forward(rows,folds,["momentum_1","momentum_5"])
    assert report["production_eligible"] is False
    assert isinstance(report["aggregate"],dict)
