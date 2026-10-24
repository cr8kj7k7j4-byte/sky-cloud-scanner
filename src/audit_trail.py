from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json


@dataclass(frozen=True)
class DecisionAuditRecord:
    decision_id: str
    symbol: str
    decision_time: str
    action: str
    decision_status: str
    market_state: str | None
    regime: str | None
    strategy_version: str
    model_version: str | None
    feature_schema_version: str | None
    rule_config_version: str | None
    data_sources: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    passed_gates: tuple[str, ...]
    blocked_gates: tuple[str, ...]
    risk_status: str | None
    execution_status: str | None
    rationale: str
    inputs_fingerprint: str | None = None

    def to_dict(self):
        return asdict(self)


def canonical_hash(payload):
    raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def finalize_record(record, input_payload=None):
    r=record if isinstance(record,DecisionAuditRecord) else DecisionAuditRecord(**record)
    item=r.to_dict()
    if not item.get("inputs_fingerprint"):
        item["inputs_fingerprint"]=canonical_hash(input_payload or {})
    item["record_fingerprint"]=canonical_hash(item)
    item["logged_at"]=datetime.now(timezone.utc).isoformat()
    return item


def append_audit_record(path, record, input_payload=None):
    item=finalize_record(record,input_payload=input_payload)
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as fh:
        fh.write(json.dumps(item,ensure_ascii=False)+"\n")
    return item


def reconstructability_check(record):
    required=[
        "decision_id","symbol","decision_time","action","decision_status",
        "strategy_version","data_sources","evidence_ids",
        "passed_gates","blocked_gates","rationale",
        "inputs_fingerprint","record_fingerprint",
    ]
    missing=[k for k in required if not record.get(k)]
    return {
        "reconstructable":not missing,
        "missing_fields":missing,
        "note":"Reconstructable means the decision can be traced; it does not validate the decision quality.",
    }
