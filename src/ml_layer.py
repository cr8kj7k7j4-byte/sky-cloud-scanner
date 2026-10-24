from dataclasses import dataclass, asdict
from statistics import mean


@dataclass(frozen=True)
class ModelPrediction:
    model: str
    expected_return_pct: float
    confidence: float
    horizon_days: int

    def to_dict(self):
        return asdict(self)


def _clip(v, lo, hi):
    return max(lo, min(hi, float(v)))


def baseline_model_predictions(features, horizon_days=5):
    """
    Transparent baseline only. This is NOT the production ML model.
    It creates deterministic proxy predictions so the ensemble contract,
    validation, ranking, and explainability paths can be tested before
    trained XGBoost/RandomForest/NN artifacts are introduced.
    """
    f = features or {}
    m1 = float(f.get("momentum_1") or 0.0)
    m5 = float(f.get("momentum_5") or 0.0)
    vr = float(f.get("volume_ratio") or 1.0)
    rs = float(f.get("relative_strength") or 0.0)
    vwap = float(f.get("vwap_distance_pct") or 0.0)
    vol = abs(float(f.get("volatility_5") or 0.0))

    rf = 0.25 * m1 + 0.45 * m5 + 0.40 * (vr - 1.0) + 0.35 * rs - 0.10 * abs(vwap)
    xgb = 0.20 * m1 + 0.55 * m5 + 0.55 * (vr - 1.0) + 0.45 * rs - 0.12 * vol
    nn = 0.35 * m1 + 0.35 * m5 + 0.25 * (vr - 1.0) + 0.30 * rs - 0.08 * abs(vwap)

    confidence = _clip(
        0.45 + 0.05 * min(abs(m5), 5) + 0.05 * min(max(vr - 1.0, 0.0), 2.0),
        0.0,
        0.90,
    )

    return [
        ModelPrediction("RF_BASELINE", round(rf, 3), confidence, horizon_days),
        ModelPrediction("XGB_BASELINE", round(xgb, 3), confidence, horizon_days),
        ModelPrediction("NN_BASELINE", round(nn, 3), confidence, horizon_days),
    ]


def ensemble(predictions, regime_label=None):
    predictions = list(predictions or [])
    if not predictions:
        return {
            "status": "NO_MODEL_OUTPUT",
            "expected_return_pct": None,
            "confidence": 0.0,
            "consensus": "NEUTRAL",
            "model_count": 0,
            "dispersion": None,
        }

    vals = [float(p.expected_return_pct) for p in predictions]
    confs = [float(p.confidence) for p in predictions]
    exp = mean(vals)
    dispersion = max(vals) - min(vals) if len(vals) > 1 else 0.0

    # Slightly reduce confidence when model disagreement is large.
    conf = max(0.0, mean(confs) - min(0.25, dispersion / 20.0))

    if regime_label and str(regime_label).startswith("BEAR"):
        exp *= 0.75
    elif regime_label and str(regime_label).startswith("BULL"):
        exp *= 1.05

    consensus = "BULLISH" if exp >= 1.0 else "BEARISH" if exp <= -1.0 else "NEUTRAL"
    return {
        "status": "BASELINE_ONLY",
        "expected_return_pct": round(exp, 3),
        "confidence": round(conf, 3),
        "consensus": consensus,
        "model_count": len(predictions),
        "dispersion": round(dispersion, 3),
        "production_eligible": False,
        "reason": "尚未接入經 Walk-forward / OOS 驗證的正式模型",
    }
