from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib


RULE_REGISTRY_SCHEMA_VERSION = "1.0.0"


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


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(record):
    item = record.to_dict() if hasattr(record, "to_dict") else dict(record)
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_registry(path):
    p = Path(path)
    if not p.exists():
        return {
            "schema_version": RULE_REGISTRY_SCHEMA_VERSION,
            "champion_configuration": None,
            "rules": {},
            "history": [],
        }
    return json.loads(p.read_text(encoding="utf-8"))


def save_registry(path, payload):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def register_rule(path, record):
    payload = load_registry(path)
    item = record.to_dict() if isinstance(record, RuleRecord) else dict(record)
    item["fingerprint"] = fingerprint(item)

    rule_id = item["rule_id"]
    payload.setdefault("rules", {}).setdefault(rule_id, []).append(item)
    payload.setdefault("history", []).append({
        "event": "REGISTER_RULE",
        "rule_id": rule_id,
        "version": item["version"],
        "timestamp": utc_now(),
        "fingerprint": item["fingerprint"],
    })
    save_registry(path, payload)
    return payload


def latest_rule_version(payload, rule_id):
    versions = payload.get("rules", {}).get(rule_id, [])
    return versions[-1] if versions else None


def validate_champion_config(payload, config):
    reasons = []
    for rule_id, version in config.get("rules", {}).items():
        versions = payload.get("rules", {}).get(rule_id, [])
        match = next((x for x in versions if x.get("version") == version), None)
        if match is None:
            reasons.append(f"{rule_id}@{version}:not_registered")
            continue
        if not match.get("production_enabled"):
            reasons.append(f"{rule_id}@{version}:not_production_enabled")
        validation = match.get("validation", {})
        required = [
            "walk_forward_passed",
            "oos_passed",
            "cost_stress_passed",
            "leakage_check_passed",
            "paper_trade_passed",
        ]
        missing = [k for k in required if not validation.get(k)]
        if missing:
            reasons.append(f"{rule_id}@{version}:missing_validation:{','.join(missing)}")
    return {"valid": not reasons, "reasons": reasons}


def set_champion_configuration(path, config):
    payload = load_registry(path)
    check = validate_champion_config(payload, config)
    if not check["valid"]:
        raise ValueError("invalid champion configuration: " + "; ".join(check["reasons"]))

    champion = {
        "config_id": config["config_id"],
        "version": config["version"],
        "rules": dict(config["rules"]),
        "model_version": config.get("model_version"),
        "feature_schema_version": config.get("feature_schema_version"),
        "effective_from": config.get("effective_from") or utc_now(),
        "rollback_to": config.get("rollback_to"),
        "notes": config.get("notes", ""),
    }
    payload["champion_configuration"] = champion
    payload.setdefault("history", []).append({
        "event": "SET_CHAMPION",
        "config_id": champion["config_id"],
        "version": champion["version"],
        "timestamp": utc_now(),
    })
    save_registry(path, payload)
    return payload


def rollback_champion(path, prior_config):
    payload = load_registry(path)
    previous = payload.get("champion_configuration")
    payload["champion_configuration"] = dict(prior_config)
    payload.setdefault("history", []).append({
        "event": "ROLLBACK_CHAMPION",
        "from": previous,
        "to": prior_config,
        "timestamp": utc_now(),
    })
    save_registry(path, payload)
    return payload
