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
