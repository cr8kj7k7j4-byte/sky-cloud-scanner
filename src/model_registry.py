from dataclasses import dataclass, asdict
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone


@dataclass(frozen=True)
class ModelRecord:
    name: str
    version: str
    status: str
    production_eligible: bool
    metrics: dict
    validation: dict
    notes: str = ""

    def to_dict(self):
        return asdict(self)


def _load(path):
    p = Path(path)
    if not p.exists():
        return {"champion": None, "challengers": [], "history": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(path, payload):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def register_model(path, record):
    payload = _load(path)
    item = record.to_dict() if isinstance(record, ModelRecord) else dict(record)
    payload.setdefault("history", []).append(item)

    if item.get("production_eligible"):
        current = payload.get("champion")
        if current is None:
            payload["champion"] = item
        else:
            new_score = _selection_score(item.get("metrics", {}))
            old_score = _selection_score(current.get("metrics", {}))
            if new_score > old_score:
                payload.setdefault("challengers", []).append(current)
                payload["champion"] = item
            else:
                payload.setdefault("challengers", []).append(item)
    else:
        payload.setdefault("challengers", []).append(item)

    _save(path, payload)
    return payload


def _selection_score(metrics):
    """
    Engineering ranking only.
    It is NOT a probability of profit and NOT a guarantee of future returns.
    Preference: positive expectancy/PF, lower drawdown, and stability.
    """
    expectancy_r = float(metrics.get("expectancy_r") or 0.0)
    profit_factor = float(metrics.get("profit_factor") or 0.0)
    max_drawdown_r = abs(float(metrics.get("max_drawdown_r") or 0.0))
    stability = float(metrics.get("stability_score") or 0.0)
    return (
        expectancy_r * 4.0
        + max(profit_factor - 1.0, 0.0) * 2.0
        + stability
        - max_drawdown_r * 0.5
    )


def registry_snapshot(path):
    return _load(path)


# Legacy research compatibility API. Canonical governance remains P0-G.
def baseline_model_card():
    return ModelRecord(
        name="sky-ranking-transparent-baseline",
        version="0.1",
        status="RESEARCH_ONLY",
        production_eligible=False,
        metrics={},
        validation={"status": "RESEARCH_ONLY"},
        notes="未訓練模型；僅用於 ranking contract 與歷史研究重現。",
    )


def can_promote(model_card, *, min_trades=200, min_oos_pf=1.10,
                min_oos_expectancy_r=0.05, max_drawdown_r=None):
    card = model_card.to_dict() if hasattr(model_card, "to_dict") else dict(model_card or {})
    metrics = dict(card.get("metrics") or {})
    reasons = []
    if int(metrics.get("oos_trades") or 0) < min_trades:
        reasons.append("OOS樣本數不足")
    if float(metrics.get("oos_pf") or 0.0) < min_oos_pf:
        reasons.append("OOS PF 未達門檻")
    if float(metrics.get("oos_expectancy_r") or 0.0) < min_oos_expectancy_r:
        reasons.append("OOS Expectancy 未達門檻")
    if max_drawdown_r is not None and metrics.get("oos_max_drawdown_r") is not None:
        if abs(float(metrics["oos_max_drawdown_r"])) > abs(float(max_drawdown_r)):
            reasons.append("OOS 最大回撤超過門檻")
    return {"allowed": not reasons, "reasons": reasons, "schema_version": "compat-1.0"}


RULE_REGISTRY_SCHEMA_VERSION = "1.0.0"
CORE_RULE_IDS = (
    "market_gate",
    "sector_rs_gate",
    "anti_chase_gate",
    "phase_gate",
    "setup_gate",
    "trigger_gate",
    "rr_gate",
)


@dataclass(frozen=True)
class RuleRecord:
    rule_id: str
    version: str
    status: str
    production_enabled: bool
    owner_module: str
    rationale: str
    evidence: dict
    validation: dict
    rollback: dict
    created_at: str
    notes: str = ""

    def to_dict(self):
        return asdict(self)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(item):
    payload = json.dumps(dict(item), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def register_rule(path, record):
    payload = _load(path)
    payload.setdefault("rule_registry_schema_version", RULE_REGISTRY_SCHEMA_VERSION)
    payload.setdefault("rules", {})
    item = record.to_dict() if isinstance(record, RuleRecord) else dict(record)
    item["fingerprint"] = _fingerprint(item)
    rid = item["rule_id"]
    payload["rules"].setdefault(rid, []).append(item)
    payload.setdefault("history", []).append({
        "event": "REGISTER_RULE",
        "rule_id": rid,
        "version": item["version"],
        "timestamp": _utc_now(),
        "fingerprint": item["fingerprint"],
    })
    _save(path, payload)
    return payload


def build_champion_config(*, config_id, version, rule_versions, model_version=None,
                          feature_schema_version=None, rollback_to=None,
                          effective_from=None, notes=""):
    missing = [r for r in CORE_RULE_IDS if r not in rule_versions]
    extra = [r for r in rule_versions if r not in CORE_RULE_IDS]
    if missing:
        raise ValueError(f"missing core rules: {missing}")
    if extra:
        raise ValueError(f"unknown rules: {extra}")
    return {
        "config_id": config_id,
        "version": version,
        "rules": dict(rule_versions),
        "model_version": model_version,
        "feature_schema_version": feature_schema_version,
        "rollback_to": rollback_to,
        "effective_from": effective_from,
        "notes": notes,
    }


def validate_champion_config(payload, config):
    reasons = []
    for rule_id, version in dict(config.get("rules") or {}).items():
        versions = dict(payload.get("rules") or {}).get(rule_id, [])
        match = next((x for x in versions if x.get("version") == version), None)
        if match is None:
            reasons.append(f"{rule_id}@{version}:not_registered")
            continue
        if not match.get("production_enabled"):
            reasons.append(f"{rule_id}@{version}:not_production_enabled")
        required = (
            "walk_forward_passed", "oos_passed", "cost_stress_passed",
            "leakage_check_passed", "paper_trade_passed",
        )
        missing = [k for k in required if not dict(match.get("validation") or {}).get(k)]
        if missing:
            reasons.append(f"{rule_id}@{version}:missing_validation:{','.join(missing)}")
    return {"valid": not reasons, "reasons": reasons}


def set_champion_configuration(path, config):
    payload = _load(path)
    check = validate_champion_config(payload, config)
    if not check["valid"]:
        raise ValueError("invalid champion configuration: " + "; ".join(check["reasons"]))
    champion = {
        **dict(config),
        "effective_from": config.get("effective_from") or _utc_now(),
    }
    payload["champion_configuration"] = champion
    payload.setdefault("history", []).append({
        "event": "SET_CHAMPION",
        "config_id": champion["config_id"],
        "version": champion["version"],
        "timestamp": _utc_now(),
    })
    _save(path, payload)
    return payload


def rollback_champion(path, prior_config):
    payload = _load(path)
    previous = payload.get("champion_configuration")
    payload["champion_configuration"] = dict(prior_config)
    payload.setdefault("history", []).append({
        "event": "ROLLBACK_CHAMPION",
        "from": previous,
        "to": prior_config,
        "timestamp": _utc_now(),
    })
    _save(path, payload)
    return payload


def promotion_readiness(*, walk_forward=False, oos=False, cost_stress=False,
                        leakage_check=False, survivorship_review=False,
                        regime_stability=False, paper_trade=False,
                        sample_sufficient=False):
    checks = {
        "walk_forward": bool(walk_forward),
        "oos": bool(oos),
        "cost_stress": bool(cost_stress),
        "leakage_check": bool(leakage_check),
        "survivorship_review": bool(survivorship_review),
        "regime_stability": bool(regime_stability),
        "paper_trade": bool(paper_trade),
        "sample_sufficient": bool(sample_sufficient),
    }
    failed = [k for k, ok in checks.items() if not ok]
    return {
        "promotable": not failed,
        "checks": checks,
        "failed_checks": failed,
        "note": "Promotion readiness is governance status, not forecast probability.",
    }



def _deep_get(item, *paths, default=None):
    """Return the first non-None value from dotted-path candidates."""
    for path in paths:
        cur = item
        ok = True
        for part in str(path).split("."):
            if not isinstance(cur, dict) or part not in cur:
                ok = False
                break
            cur = cur[part]
        if ok and cur is not None:
            return cur
    return default


def evaluate_shadow_sample_sufficiency(
    records,
    *,
    min_samples=200,
    min_trading_days=20,
    min_regimes=2,
    min_outcome_complete_ratio=0.95,
    max_symbol_share=0.20,
):
    """Evidence-sufficiency gate for Shadow/Paper observations.

    This is a governance gate, not a win-rate or profitability estimate.
    Default thresholds are conservative candidate values and may be revised
    only through documented research/governance changes.
    """
    rows = [dict(x) for x in (records or [])]
    n = len(rows)

    days = set()
    regimes = set()
    symbols = {}
    outcome_complete = 0

    for row in rows:
        observed = str(row.get("observed_at") or "")
        if len(observed) >= 10:
            days.add(observed[:10])

        regime = _deep_get(
            row,
            "research_context.regime",
            "ml.regime.label",
            "regime",
        )
        if regime not in (None, "", "UNKNOWN"):
            regimes.add(str(regime))

        symbol = str(row.get("symbol") or "")
        if symbol:
            symbols[symbol] = symbols.get(symbol, 0) + 1

        outcome = row.get("outcome")
        if isinstance(outcome, dict):
            status = str(outcome.get("status") or "").upper()
            if status in {"COMPLETE", "CLOSED", "FINAL"}:
                outcome_complete += 1
            elif (
                outcome.get("r_multiple") is not None
                or outcome.get("net_pnl") is not None
            ):
                outcome_complete += 1

    outcome_complete_ratio = (
        outcome_complete / n if n else 0.0
    )
    top_symbol_count = max(symbols.values()) if symbols else 0
    top_symbol_share = top_symbol_count / n if n else 0.0

    checks = {
        "sample_count": n >= int(min_samples),
        "trading_days": len(days) >= int(min_trading_days),
        "regime_coverage": len(regimes) >= int(min_regimes),
        "outcome_completeness": (
            outcome_complete_ratio >= float(min_outcome_complete_ratio)
        ),
        "symbol_concentration": top_symbol_share <= float(max_symbol_share),
    }
    failed = [k for k, ok in checks.items() if not ok]

    return {
        "sufficient": not failed,
        "checks": checks,
        "failed_checks": failed,
        "observed": {
            "samples": n,
            "trading_days": len(days),
            "regimes": sorted(regimes),
            "regime_count": len(regimes),
            "outcome_complete": outcome_complete,
            "outcome_complete_ratio": round(outcome_complete_ratio, 6),
            "unique_symbols": len(symbols),
            "top_symbol_share": round(top_symbol_share, 6),
        },
        "thresholds": {
            "min_samples": int(min_samples),
            "min_trading_days": int(min_trading_days),
            "min_regimes": int(min_regimes),
            "min_outcome_complete_ratio": float(min_outcome_complete_ratio),
            "max_symbol_share": float(max_symbol_share),
        },
        "note": (
            "Shadow Sample Sufficiency 只判斷證據量與代表性，"
            "不代表勝率、獲利機率或策略有效性。"
        ),
    }


PROMOTION_SCORECARD_WEIGHTS = {
    "sample_sufficient": 12,
    "walk_forward": 12,
    "oos": 14,
    "cost_stress": 10,
    "leakage_check": 10,
    "survivorship_review": 8,
    "regime_stability": 10,
    "paper_trade": 10,
    "positive_expectancy": 7,
    "profit_factor": 4,
    "drawdown_control": 3,
}


def build_promotion_scorecard(
    evidence,
    *,
    artifact_type="MODEL",
    min_expectancy_r=0.0,
    min_profit_factor=1.0,
    max_drawdown_r=None,
):
    """Canonical Ranking/Model promotion evidence scorecard.

    Score is evidence-readiness only. A score of 100 is NOT a win rate,
    probability of profit, or automatic production authorization.
    Every hard gate must pass before governance review can start.
    """
    e = dict(evidence or {})
    metrics = dict(e.get("metrics") or {})
    validation = dict(e.get("validation") or {})

    expectancy = float(
        metrics.get("oos_expectancy_r", metrics.get("expectancy_r", 0.0))
        or 0.0
    )
    pf = float(
        metrics.get("oos_pf", metrics.get("profit_factor", 0.0))
        or 0.0
    )
    drawdown_raw = metrics.get(
        "oos_max_drawdown_r", metrics.get("max_drawdown_r")
    )
    drawdown = (
        abs(float(drawdown_raw)) if drawdown_raw is not None else None
    )

    checks = {
        "sample_sufficient": bool(
            validation.get("sample_sufficient", e.get("sample_sufficient", False))
        ),
        "walk_forward": bool(
            validation.get("walk_forward_passed", validation.get("walk_forward", False))
        ),
        "oos": bool(
            validation.get("oos_passed", validation.get("oos", False))
        ),
        "cost_stress": bool(
            validation.get("cost_stress_passed", validation.get("cost_stress", False))
        ),
        "leakage_check": bool(
            validation.get("leakage_check_passed", validation.get("leakage_check", False))
        ),
        "survivorship_review": bool(
            validation.get("survivorship_reviewed", validation.get("survivorship_review", False))
        ),
        "regime_stability": bool(
            validation.get("regime_stability_passed", validation.get("regime_stability", False))
        ),
        "paper_trade": bool(
            validation.get("paper_trade_passed", validation.get("paper_trade", False))
        ),
        "positive_expectancy": expectancy > float(min_expectancy_r),
        "profit_factor": pf > float(min_profit_factor),
        "drawdown_control": (
            True
            if max_drawdown_r is None
            else drawdown is not None
            and drawdown <= abs(float(max_drawdown_r))
        ),
    }

    earned = sum(
        PROMOTION_SCORECARD_WEIGHTS[k]
        for k, ok in checks.items()
        if ok
    )
    total = sum(PROMOTION_SCORECARD_WEIGHTS.values())
    score = round(100.0 * earned / total, 1) if total else 0.0
    failed = [k for k, ok in checks.items() if not ok]

    hard_gates = (
        "sample_sufficient",
        "walk_forward",
        "oos",
        "cost_stress",
        "leakage_check",
        "survivorship_review",
        "regime_stability",
        "paper_trade",
        "positive_expectancy",
        "profit_factor",
        "drawdown_control",
    )
    promotable_to_review = all(checks[k] for k in hard_gates)

    return {
        "artifact_type": str(artifact_type or "MODEL").upper(),
        "score": score,
        "meaning": "升版證據成熟度，不代表勝率或獲利機率",
        "checks": checks,
        "failed_checks": failed,
        "metrics_used": {
            "expectancy_r": expectancy,
            "profit_factor": pf,
            "max_drawdown_r": drawdown,
        },
        "thresholds": {
            "min_expectancy_r": float(min_expectancy_r),
            "min_profit_factor": float(min_profit_factor),
            "max_drawdown_r": (
                None if max_drawdown_r is None else abs(float(max_drawdown_r))
            ),
        },
        "promotable_to_governance_review": promotable_to_review,
        "production_eligible": False,
        "note": (
            "Scorecard 全通過只代表可進治理審查；"
            "仍須由 P0-G 明確核准 Champion Configuration。"
        ),
    }



def build_shadow_promotion_dashboard(
    records,
    *,
    promotion_evidence=None,
    artifact_type="RANKING",
    min_samples=200,
    min_trading_days=20,
    min_regimes=2,
    min_outcome_complete_ratio=0.95,
    max_symbol_share=0.20,
    min_expectancy_r=0.0,
    min_profit_factor=1.0,
    max_drawdown_r=None,
):
    """Build the canonical P0-G Shadow evidence/promotion dashboard."""
    suff = evaluate_shadow_sample_sufficiency(
        records,
        min_samples=min_samples,
        min_trading_days=min_trading_days,
        min_regimes=min_regimes,
        min_outcome_complete_ratio=min_outcome_complete_ratio,
        max_symbol_share=max_symbol_share,
    )
    obs = dict(suff["observed"])
    th = dict(suff["thresholds"])

    gaps = {
        "samples_remaining": max(0, th["min_samples"] - obs["samples"]),
        "trading_days_remaining": max(
            0, th["min_trading_days"] - obs["trading_days"]
        ),
        "regimes_remaining": max(
            0, th["min_regimes"] - obs["regime_count"]
        ),
        "outcome_completeness_gap": round(
            max(
                0.0,
                th["min_outcome_complete_ratio"]
                - obs["outcome_complete_ratio"],
            ),
            6,
        ),
        "symbol_concentration_excess": round(
            max(
                0.0,
                obs["top_symbol_share"] - th["max_symbol_share"],
            ),
            6,
        ),
    }

    evidence = dict(promotion_evidence or {})
    validation = dict(evidence.get("validation") or {})
    validation["sample_sufficient"] = suff["sufficient"]
    evidence["validation"] = validation
    evidence["sample_sufficient"] = suff["sufficient"]

    scorecard = build_promotion_scorecard(
        evidence,
        artifact_type=artifact_type,
        min_expectancy_r=min_expectancy_r,
        min_profit_factor=min_profit_factor,
        max_drawdown_r=max_drawdown_r,
    )

    if scorecard["promotable_to_governance_review"]:
        stage = "GOVERNANCE_REVIEW_READY"
    elif suff["sufficient"]:
        stage = "SAMPLE_READY"
    else:
        # W4 governance contract: insufficient forward evidence must never be
        # presented as an implicitly progressing/passing state.
        stage = "WAITING_FOR_FUTURE_SAMPLE"

    blockers = []
    blockers.extend(
        f"sample:{x}" for x in suff.get("failed_checks", [])
    )
    blockers.extend(
        f"promotion:{x}"
        for x in scorecard.get("failed_checks", [])
        if x != "sample_sufficient"
    )

    return {
        "schema_version": "1.1",
        "stage": stage,
        "artifact_type": str(artifact_type or "RANKING").upper(),
        "sample_sufficiency": suff,
        "sample_gaps": gaps,
        "promotion_scorecard": scorecard,
        "blocking_items": blockers,
        "summary": {
            "samples": obs["samples"],
            "trading_days": obs["trading_days"],
            "regime_count": obs["regime_count"],
            "outcome_complete_ratio": obs["outcome_complete_ratio"],
            "top_symbol_share": obs["top_symbol_share"],
            "promotion_score": scorecard["score"],
            "promotable_to_governance_review": scorecard[
                "promotable_to_governance_review"
            ],
        },
        "note": (
            "Dashboard 用於證據累積與升版治理，不是交易勝率、"
            "報酬預測或自動 Production Promotion。"
        ),
    }
