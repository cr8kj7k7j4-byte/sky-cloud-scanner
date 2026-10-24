from dataclasses import dataclass, asdict
from datetime import date
from statistics import mean

from .model_training import train_and_evaluate


@dataclass(frozen=True)
class FoldResult:
    fold_index: int
    train_n: int
    validate_n: int
    test_n: int
    models: dict

    def to_dict(self):
        return asdict(self)


def _day(text):
    return date.fromisoformat(str(text)[:10])


def _between(rows, start, end):
    s=_day(start); e=_day(end)
    out=[]
    for row in rows or []:
        try:
            d=_day(row.get("observed_at"))
        except Exception:
            continue
        if s <= d <= e:
            out.append(row)
    return out


def evaluate_walk_forward(dataset_rows, folds, feature_keys, target_key="r_multiple"):
    fold_results=[]
    for idx,fold in enumerate(folds,1):
        train=_between(dataset_rows,fold.train_start,fold.train_end)
        validate=_between(dataset_rows,fold.validate_start,fold.validate_end)
        test=_between(dataset_rows,fold.test_start,fold.test_end)

        comparison=train_and_evaluate(
            train_rows=train,
            test_rows=test,
            feature_keys=feature_keys,
            target_key=target_key,
            random_state=42+idx,
        )
        fold_results.append(FoldResult(
            fold_index=idx,
            train_n=len(train),
            validate_n=len(validate),
            test_n=len(test),
            models=comparison["results"],
        ).to_dict())

    aggregate={}
    names=sorted({
        name
        for fold in fold_results
        for name in fold["models"].keys()
    })
    for name in names:
        oks=[
            fold["models"][name]
            for fold in fold_results
            if fold["models"].get(name,{}).get("status")=="OK"
        ]
        metrics=[x["metrics"] for x in oks]
        aggregate[name]={
            "folds_ok":len(metrics),
            "mean_mae":round(mean([m["mae"] for m in metrics]),6) if metrics else None,
            "mean_rmse":round(mean([m["rmse"] for m in metrics]),6) if metrics else None,
            "mean_directional_accuracy":round(mean([m["directional_accuracy"] for m in metrics]),6) if metrics else None,
            "mean_expectancy_r":round(mean([m["expectancy_r"] for m in metrics]),6) if metrics else None,
            "mean_pf":round(mean([m["pf"] for m in metrics if m["pf"] is not None]),6) if any(m["pf"] is not None for m in metrics) else None,
            "production_eligible":False,
        }

    return {
        "folds":fold_results,
        "aggregate":aggregate,
        "production_eligible":False,
        "reason":"Walk-forward 比較完成不等於正式可交易；仍須 Promotion Gate 與 Paper Trading",
    }
