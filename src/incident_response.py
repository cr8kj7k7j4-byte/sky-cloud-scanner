from __future__ import annotations

from dataclasses import dataclass, asdict


SEVERITY_ORDER = {"SEV0": 0, "SEV1": 1, "SEV2": 2, "SEV3": 3}

INCIDENT_TYPES = {
    "DATA_STALE",
    "DATA_SOURCE_DOWN",
    "OFFICIAL_CHAIN_INCOMPLETE",
    "EXECUTION_COST_ANOMALY",
    "RISK_ENGINE_ANOMALY",
    "MODEL_DRIFT",
    "MONITORING_DOWN",
    "STATE_STORE_DOWN",
    "REGIME_MISMATCH",
    "SECURITY_SECRET_EXPOSURE",
}


@dataclass(frozen=True)
class Incident:
    incident_type: str
    severity: str
    detected_at: str
    source: str
    detail: str
    affected_modules: tuple[str, ...] = ()
    resolved: bool = False

    def to_dict(self):
        return asdict(self)


def validate_incident(incident):
    i = incident if isinstance(incident, Incident) else Incident(**incident)
    if i.incident_type not in INCIDENT_TYPES:
        raise ValueError(f"unknown incident_type: {i.incident_type}")
    if i.severity not in SEVERITY_ORDER:
        raise ValueError(f"unknown severity: {i.severity}")
    return i


def required_action(incident):
    i = validate_incident(incident)

    if i.severity == "SEV0":
        return {
            "mode": "LOCKDOWN",
            "new_entries_allowed": False,
            "live_activation_allowed": False,
            "rollback_required": True,
            "manual_review_required": True,
        }

    if i.severity == "SEV1":
        return {
            "mode": "DEFENSIVE",
            "new_entries_allowed": False,
            "live_activation_allowed": False,
            "rollback_required": i.incident_type in {
                "RISK_ENGINE_ANOMALY",
                "SECURITY_SECRET_EXPOSURE",
                "EXECUTION_COST_ANOMALY",
            },
            "manual_review_required": True,
        }

    if i.severity == "SEV2":
        return {
            "mode": "CAUTION",
            "new_entries_allowed": False,
            "live_activation_allowed": False,
            "rollback_required": False,
            "manual_review_required": True,
        }

    return {
        "mode": "OBSERVE_ONLY",
        "new_entries_allowed": False,
        "live_activation_allowed": False,
        "rollback_required": False,
        "manual_review_required": False,
    }
