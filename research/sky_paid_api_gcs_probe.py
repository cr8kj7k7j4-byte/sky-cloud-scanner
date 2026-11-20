"""Two independent GitHub Runner GCS-CAS research acceptance, no paid data calls.

This script writes only tiny synthetic records to a per-run research prefix.
It cannot call Fugle, place orders, or enable a Production strategy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from google.cloud import storage

from research.sky_paid_api_dedup_contract import (
    canonical_request_key, finalize_ready, reserve,
)
from research.sky_paid_api_gcs_store import GcsAtomicStore

PREFIX = "sky/research/paid-api-dedup/cas-acceptance-v1"
OUT = Path("output/gcs_paid_api_cas_acceptance")


def identity():
    run_id = os.environ["GITHUB_RUN_ID"]
    if not run_id.isdecimal():
        raise ValueError("INVALID_GITHUB_RUN_ID")
    return canonical_request_key(
        "SYNTHETIC_NO_FUGLE", "/no-provider-api",
        {"acceptance": "two_independent_runners", "run_id": run_id},
        "NO_PAID_PROVIDER_ENTITLEMENT", "RESEARCH_ONLY",
    )


def bucket_client():
    name = os.environ.get("SKY_RESEARCH_GCS_BUCKET", "").strip()
    if not name or "/" in name:
        raise ValueError("RESEARCH_GCS_BUCKET_NOT_CONFIGURED")
    return storage.Client().bucket(name)


def receipt_object(run_id: str, slot: str):
    if slot not in ("A", "B"):
        raise ValueError("INVALID_CONTENDER_SLOT")
    return f"{PREFIX}/receipts/{run_id}/{slot}.json"


def write_local(document, filename):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / filename).write_text(
        json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )


def contender(slot: str):
    bucket = bucket_client()
    run_id = os.environ["GITHUB_RUN_ID"]
    sha = os.environ["GITHUB_SHA"]
    key = identity()
    store = GcsAtomicStore(bucket, prefix=PREFIX)
    owner = f"{run_id}:{slot}"
    decision = reserve(store, key, owner, "synthetic-first-attempt")
    if decision == "CALL_ONCE":
        data = json.dumps({
            "schema": "SKY_GCS_CAS_SYNTHETIC_RESULT_V1",
            "run_id": run_id, "request_key": key,
            "synthetic": True, "paid_provider_requests": 0,
            "production_eligible": False, "automatic_order": False,
        }, sort_keys=True).encode("utf-8")
        uri, digest = store.persist_research_result_if_absent(key, data)
        if not finalize_ready(store, key, owner, "synthetic-first-attempt",
                              uri, digest, quota_units=0, usage_source="NO_PROVIDER_CALL"):
            raise ValueError("REMOTE_CAS_FINALIZE_READY_FAILED")
    elif decision not in ("BLOCK_IN_FLIGHT", "REUSE_READY"):
        raise ValueError("RESERVATION_NOT_SAFE:" + str(decision))
    record = {
        "schema": "SKY_GCS_CAS_TWO_RUNNER_CONTENDER_V1",
        "run_id": run_id, "sha": sha, "slot": slot, "request_key": key,
        "owner_run_id": owner, "decision": decision,
        "synthetic": True, "paid_provider_requests": 0,
        "production_eligible": False, "automatic_order": False,
        "trade_action": "禁止交易",
    }
    write_local(record, f"contender-{slot}.json")
    bucket.blob(receipt_object(run_id, slot)).upload_from_string(
        json.dumps(record, sort_keys=True).encode("utf-8"),
        content_type="application/json", if_generation_match=0,
    )
    print(json.dumps({"slot": slot, "decision": decision, "synthetic": True},
                     ensure_ascii=False))


def verify():
    bucket = bucket_client()
    run_id = os.environ["GITHUB_RUN_ID"]
    key = identity()
    store = GcsAtomicStore(bucket, prefix=PREFIX)
    rows = []
    for slot in ("A", "B"):
        blob = bucket.blob(receipt_object(run_id, slot))
        blob.reload()
        item = json.loads(blob.download_as_bytes(
            if_generation_match=int(blob.generation)))
        if (item.get("run_id") != run_id or item.get("request_key") != key
                or item.get("slot") != slot or item.get("synthetic") is not True
                or item.get("paid_provider_requests") != 0
                or item.get("production_eligible") is not False
                or item.get("automatic_order") is not False):
            raise ValueError("CONTENDER_RECEIPT_NOT_VERIFIED")
        rows.append(item)
    winners = [x for x in rows if x["decision"] == "CALL_ONCE"]
    losers = [x for x in rows if x["decision"] in ("BLOCK_IN_FLIGHT", "REUSE_READY")]
    if len(winners) != 1 or len(losers) != 1:
        raise ValueError("CROSS_RUNNER_ATOMIC_RESERVATION_FAILED")
    pair = store.read(key)
    if pair is None or pair[0].state != "READY":
        raise ValueError("FINAL_DURABLE_READY_NOT_PRESENT")
    current, version = pair
    if (current.owner_run_id != winners[0]["owner_run_id"]
            or current.quota_units != 0 or current.usage_source != "NO_PROVIDER_CALL"
            or not store.verify_durable_result(current.result_uri, current.result_sha256)):
        raise ValueError("CROSS_RUNNER_RESULT_INTEGRITY_FAILED")
    if reserve(store, key, f"{run_id}:verifier", "readback") != "REUSE_READY":
        raise ValueError("THIRD_RUNNER_REUSE_NOT_VERIFIED")
    proof = {
        "schema": "SKY_GCS_PAID_API_CAS_CROSS_RUNNER_PROOF_V1",
        "status": "PASS_RESEARCH_ONLY", "run_id": run_id,
        "sha": os.environ["GITHUB_SHA"], "request_key": key,
        "independent_contender_slots": ["A", "B"],
        "call_once_count": 1, "blocked_or_reused_count": 1,
        "durable_result_digest_verified": True,
        "remote_cas_generation_version": version,
        "cross_workflow_runtime_lease_verified": False,
        "cross_runner_remote_atomic_store_verified": True,
        "paid_provider_requests": 0,
        "provider_request_id": None,
        "production_eligible": False, "automatic_order": False,
        "trade_action": "禁止交易",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_local(proof, "proof.json")
    print(json.dumps(proof, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("contender", "verify"), required=True)
    parser.add_argument("--slot", choices=("A", "B"))
    args = parser.parse_args()
    try:
        if args.mode == "contender":
            if not args.slot:
                raise ValueError("CONTENDER_SLOT_REQUIRED")
            contender(args.slot)
        else:
            verify()
    except Exception as exc:
        write_local({
            "schema": "SKY_GCS_CAS_FAIL_CLOSED_V1",
            "status": "HOLD",
            "reason": type(exc).__name__ + ":" + str(exc)[:120],
            "production_eligible": False, "automatic_order": False,
            "paid_provider_requests": 0, "trade_action": "禁止交易",
        }, f"failure-{args.mode}{('-' + args.slot) if args.slot else ''}.json")
        raise


if __name__ == "__main__":
    main()
