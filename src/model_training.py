from dataclasses import dataclass, asdict
from math import sqrt
from statistics import mean

MODEL_COMPARISON_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class RegressionMetrics:
    n: int
    mae: float | None
    rmse: float | None
    directional_accuracy: float | None
    expectancy_r: float | None
    pf: float | None
    max_drawdown_r: float | None

    def to_dict(self):
        return asdict(self)


def _as_xy(rows, feature_keys, target_key="r_multiple"):
    X=[]; y=[]; kept=[]
    for row in rows or []:
        feats=row.get("features") or {}
        target=(row.get("targets") or {}).get(target_key)
        if target is None:
            continue
        vector=[]
        ok=True
        for key in feature_keys:
            value=feats.get(key)
            if value is None:
                ok=False
                break
            try:
                vector.append(float(value))
            except Exception:
                ok=False
                break
        if not ok:
            continue
        X.append(vector); y.append(float(target)); kept.append(row)
    return X,y,kept


def _max_drawdown_r(values):
    equity=0.0
    peak=0.0
    worst=0.0
    for v in values:
        equity += float(v)
        peak=max(peak,equity)
        worst=min(worst,equity-peak)
    return worst


def evaluate_predictions(y_true, y_pred):
    y_true=list(map(float,y_true or []))
    y_pred=list(map(float,y_pred or []))
    n=min(len(y_true),len(y_pred))
    if n == 0:
        return RegressionMetrics(0,None,None,None,None,None,None)
    y_true=y_true[:n]; y_pred=y_pred[:n]
    errors=[abs(a-b) for a,b in zip(y_true,y_pred)]
    mae=mean(errors)
    rmse=sqrt(mean([(a-b)**2 for a,b in zip(y_true,y_pred)]))
    directional=mean([1.0 if (a>=0)==(b>=0) else 0.0 for a,b in zip(y_true,y_pred)])
    expectancy=mean(y_true)
    gains=sum(v for v in y_true if v>0)
    losses=abs(sum(v for v in y_true if v<0))
    pf=(gains/losses) if losses>0 else None
    return RegressionMetrics(
        n=n,
        mae=round(mae,6),
        rmse=round(rmse,6),
        directional_accuracy=round(directional,6),
        expectancy_r=round(expectancy,6),
        pf=round(pf,6) if pf is not None else None,
        max_drawdown_r=round(_max_drawdown_r(y_true),6),
    )


def available_model_factories(random_state=42):
    factories={}
    errors={}

    try:
        from sklearn.ensemble import RandomForestRegressor
        factories["RANDOM_FOREST"] = lambda: RandomForestRegressor(
            n_estimators=300,
            max_depth=6,
            min_samples_leaf=5,
            random_state=random_state,
            n_jobs=-1,
        )
    except Exception as e:
        errors["RANDOM_FOREST"]=f"{type(e).__name__}: {e}"

    try:
        from xgboost import XGBRegressor
        factories["XGBOOST"] = lambda: XGBRegressor(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
            random_state=random_state,
            n_jobs=2,
        )
    except Exception as e:
        errors["XGBOOST"]=f"{type(e).__name__}: {e}"

    try:
        from lightgbm import LGBMRegressor
        factories["LIGHTGBM"] = lambda: LGBMRegressor(
            n_estimators=300,
            max_depth=-1,
            num_leaves=31,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            verbosity=-1,
        )
    except Exception as e:
        errors["LIGHTGBM"]=f"{type(e).__name__}: {e}"

    return factories, errors


def train_and_evaluate(train_rows, test_rows, feature_keys, target_key="r_multiple", random_state=42):
    X_train,y_train,_ = _as_xy(train_rows,feature_keys,target_key)
    X_test,y_test,kept = _as_xy(test_rows,feature_keys,target_key)
    factories,errors = available_model_factories(random_state=random_state)

    results={}
    for name,factory in factories.items():
        if len(X_train) < 30 or len(X_test) < 10:
            results[name]={
                "status":"INSUFFICIENT_SAMPLE",
                "train_n":len(X_train),
                "test_n":len(X_test),
                "production_eligible":False,
            }
            continue
        try:
            model=factory()
            model.fit(X_train,y_train)
            pred=model.predict(X_test)
            metrics=evaluate_predictions(y_test,pred).to_dict()
            results[name]={
                "status":"OK",
                "train_n":len(X_train),
                "test_n":len(X_test),
                "metrics":metrics,
                "predictions":[float(x) for x in pred],
                "record_ids":[x.get("record_id") for x in kept],
                "production_eligible":False,
            }
        except Exception as e:
            results[name]={
                "status":"ERROR",
                "error":f"{type(e).__name__}: {e}",
                "production_eligible":False,
            }

    for name,error in errors.items():
        results[name]={
            "status":"DEPENDENCY_UNAVAILABLE",
            "error":error,
            "production_eligible":False,
        }

    return {
        "schema_version":MODEL_COMPARISON_SCHEMA_VERSION,
        "target":target_key,
        "feature_keys":list(feature_keys),
        "results":results,
        "production_eligible":False,
        "reason":"模型比較結果須經完整 Walk-forward/OOS、成本與 Paper Trading 後才能升格",
    }
