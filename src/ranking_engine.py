from dataclasses import dataclass, asdict
from statistics import mean

RANKING_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class RankingPrediction:
    model_name: str
    expected_r: float | None
    expected_mfe_pct: float | None
    expected_mae_pct: float | None
    probability_hit_1r: float | None
    score: float | None
    production_eligible: bool
    reason: str

    def to_dict(self):
        return asdict(self)


def _num(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def transparent_baseline_rank(features):
    """
    Research-only ranking baseline.
    This is intentionally deterministic and interpretable.
    It is NOT a trained model and can never be production eligible.
    """
    f = features or {}
    m1 = _num(f.get("momentum_1"))
    m5 = _num(f.get("momentum_5"))
    vr = _num(f.get("volume_ratio"), 1.0)
    rs = _num(f.get("relative_strength"))
    vwap = abs(_num(f.get("vwap_distance_pct")))
    vol = abs(_num(f.get("volatility_5")))
    spread = abs(_num(f.get("spread_pct")))

    score = (
        0.30 * m1
        + 0.55 * m5
        + 0.45 * (vr - 1.0)
        + 0.50 * rs
        - 0.18 * vwap
        - 0.12 * vol
        - 0.25 * spread
    )
    expected_r = score / 2.5
    expected_mfe = max(0.0, score * 0.9)
    expected_mae = min(0.0, -abs(score) * 0.35)
    p1r = max(0.0, min(1.0, 0.50 + score / 20.0))

    return RankingPrediction(
        model_name="TRANSPARENT_BASELINE",
        expected_r=round(expected_r, 4),
        expected_mfe_pct=round(expected_mfe, 4),
        expected_mae_pct=round(expected_mae, 4),
        probability_hit_1r=round(p1r, 4),
        score=round(score, 4),
        production_eligible=False,
        reason="研究用透明基準，未經 Walk-forward/OOS 驗證",
    )


def rank_candidates(candidates, predictor=None):
    predictor = predictor or transparent_baseline_rank
    ranked = []
    for item in candidates or []:
        features = item.get("feature_envelope", {}).get("features") or item.get("features") or {}
        pred = predictor(features)
        payload = dict(item)
        payload["ranking_model"] = pred.to_dict() if hasattr(pred, "to_dict") else dict(pred)
        ranked.append(payload)

    ranked.sort(
        key=lambda x: (
            x.get("ranking_model", {}).get("score") is not None,
            x.get("ranking_model", {}).get("score") or float("-inf"),
        ),
        reverse=True,
    )
    for i, item in enumerate(ranked, 1):
        item["ranking_position"] = i
    return ranked


def summarize_ranking(ranked):
    scores = [
        x.get("ranking_model", {}).get("score")
        for x in ranked or []
        if x.get("ranking_model", {}).get("score") is not None
    ]
    return {
        "schema_version": RANKING_SCHEMA_VERSION,
        "count": len(ranked or []),
        "mean_score": round(mean(scores), 4) if scores else None,
        "production_eligible": False,
        "reason": "目前 Ranking 僅研究用，不得繞過 P0-C/P0-R",
    }
