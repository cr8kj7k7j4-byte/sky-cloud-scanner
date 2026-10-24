from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ArenaResult:
    name: str
    family: str
    production_eligible: bool
    metrics: dict
    validation: dict
    notes: str = ""

    def to_dict(self):
        return asdict(self)


def score_candidate(result):
    r = result.to_dict() if isinstance(result, ArenaResult) else dict(result)
    m = r.get("metrics", {})
    v = r.get("validation", {})

    if not r.get("production_eligible"):
        return float("-inf")

    required = [
        "walk_forward_passed",
        "oos_passed",
        "cost_stress_passed",
        "leakage_check_passed",
        "paper_trade_passed",
    ]
    if not all(bool(v.get(k)) for k in required):
        return float("-inf")

    expectancy_r = float(m.get("expectancy_r") or 0.0)
    pf = float(m.get("profit_factor") or 0.0)
    max_dd_r = abs(float(m.get("max_drawdown_r") or 0.0))
    stability = float(m.get("stability_score") or 0.0)

    if expectancy_r <= 0 or pf <= 1.0:
        return float("-inf")

    return expectancy_r * 5.0 + (pf - 1.0) * 2.0 + stability - max_dd_r * 0.4


def rank_models(results):
    rows = []
    for r in results or []:
        item = r.to_dict() if isinstance(r, ArenaResult) else dict(r)
        item["arena_score"] = score_candidate(item)
        rows.append(item)

    rows.sort(
        key=lambda x: x["arena_score"],
        reverse=True,
    )
    return rows


def choose_champion(results):
    ranked = rank_models(results)
    valid = [x for x in ranked if x["arena_score"] != float("-inf")]
    return valid[0] if valid else None
