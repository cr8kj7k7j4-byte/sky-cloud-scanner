"""Append-only counterfactual follow-up linked to immutable meta observation.

This is an offline evidence contract. Only a separately certified producer can
attest price snapshots; boolean fields cannot establish independent provenance.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json

from research.sky_meta_filter_ledger import canonical
from research.sky_meta_filter_v0_1 import validate_observation, stamp, finite


def append_followup_once(observation, followup, *, root):
    original=validate_observation(observation)
    if original["outcome_status"] != "PENDING":
        raise ValueError("original_observation_must_be_pending")
    if not isinstance(followup,dict) or followup.get("schema") != "sky-meta-filter-followup-v0.1":
        raise ValueError("unsupported_followup_schema")
    if followup.get("signal_id") != observation["signal_id"]:
        raise ValueError("followup_signal_id_mismatch")
    if followup.get("production_eligible") is not False or followup.get("actual_fill") is not False:
        raise ValueError("followup_must_remain_counterfactual")
    if followup.get("counterfactual_evidence_verified") is not True:
        raise ValueError("followup_source_unverified")
    original_digest=sha256(canonical(observation)).hexdigest()
    if followup.get("observation_sha256") != original_digest:
        raise ValueError("followup_observation_digest_mismatch")
    # Derived combined row requires same-session future timestamp and finite
    # executable-proxy amounts. No use of outcomes for score/decision.
    combined=dict(observation)
    combined["exit_at"]=followup.get("exit_at")
    combined["exit_proxy"]=followup.get("exit_proxy")
    combined["counterfactual_evidence_verified"]=True
    candidate=validate_observation(combined)
    if candidate["outcome_status"] != "COUNTERFACTUAL_ONLY":
        raise ValueError("followup_is_not_completed")
    folder=Path(root)
    if not folder.is_absolute():
        raise ValueError("private_followup_root_must_be_absolute")
    # Always refer to immutable observation stored earlier in the same private
    # root, so callers cannot write followups on unarchived mock candidate IDs.
    observed=folder / original["decision_date"] / original["symbol"] / (original["signal_id"]+".json")
    if not observed.is_file() or observed.read_bytes() != canonical(observation):
        raise ValueError("original_immutable_observation_missing")
    child=folder / "followups" / original["decision_date"] / original["symbol"]
    child.mkdir(parents=True,exist_ok=True)
    dest=child / (original["signal_id"]+".json")
    bytes_=canonical(followup)
    try:
        with dest.open("xb") as f:
            f.write(bytes_)
        status="CREATED"
    except FileExistsError:
        if dest.read_bytes()!=bytes_:
            raise ValueError("immutable_followup_conflict")
        status="ALREADY_EXISTS_IDENTICAL"
    return {"signal_id": original["signal_id"],"status":status,
            "followup_sha256":sha256(bytes_).hexdigest(),
            "counterfactual_only":True,"production_eligible":False}
