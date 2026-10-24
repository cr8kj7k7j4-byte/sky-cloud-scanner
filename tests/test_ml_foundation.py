import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.feature_engine import build_features
from src.regime_engine import detect_regime
from src.ml_layer import baseline_model_predictions, ensemble
from src.explainability import explain
from src.validation import evaluate_validation_gate


def main():
    candidate = {
        "last": 50.0,
        "fugle_close": 50.0,
        "avg_price": 49.0,
        "fugle_high": 50.5,
        "fugle_low": 48.8,
        "change_pct": 3.2,
    }
    candles = [
        {"close": 47.5, "volume": 100},
        {"close": 48.0, "volume": 110},
        {"close": 48.5, "volume": 120},
        {"close": 49.0, "volume": 130},
        {"close": 49.4, "volume": 140},
        {"close": 50.0, "volume": 220},
    ]
    f = build_features(candidate, candles, market_return_pct=1.0).to_dict()
    assert f["momentum_5"] is not None
    assert f["volume_ratio"] > 1.0
    assert f["relative_strength"] == 2.2

    regime = detect_regime(index_change_pct=1.1, breadth_pct=62, volatility_pct=1.3)
    assert regime.trend == "BULL"
    assert regime.volatility == "MEDIUM"

    preds = baseline_model_predictions(f, horizon_days=5)
    ens = ensemble(preds, regime.label)
    assert ens["model_count"] == 3
    assert ens["production_eligible"] is False
    assert ens["status"] == "BASELINE_ONLY"

    exp = explain(f, ens)
    assert exp["production_shap_ready"] is False
    assert len(exp["drivers"]) >= 3

    gate = evaluate_validation_gate(
        walk_forward_passed=True,
        oos_passed=True,
        cost_stress_passed=True,
        leakage_check_passed=True,
        paper_trade_passed=False,
    )
    assert gate["production_eligible"] is False
    assert gate["status"] == "RESEARCH_ONLY"

    print("PASS P0-ML foundation tests")


if __name__ == "__main__":
    main()
