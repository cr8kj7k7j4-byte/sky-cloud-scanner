"""One-shot real Redis CAS acceptance on independent GitHub runners (no Fugle).

Uses existing REDIS_URL secret without printing it. Keys are scoped to this
research run. Proves cross-runner atomicity, NOT persistence after Redis restart
or wiring of all paid API workflows.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

import redis

from research.sky_paid_api_dedup_contract import (
    canonical_request_key, finalize_ready, reserve,
)
from research.sky_paid_api_redis_store import RedisAtomicStore

PREFIX = "sky:research:paid-api-dedup:redis-acceptance-v1"
OUT = Path("output/redis_paid_api_cas_acceptance")


def client():
    url = os.environ.get("REDIS_URL")
    if not url or not url.startswith(("redis://", "rediss://")):
        raise ValueError("REDIS_URL_EXISTING_SECRET_MISSING")
    return redis.Redis.from_url(
        url, decode_responses=False, socket_connect_timeout=5,
        socket_timeout=5, retry_on_timeout=False,
    )


def identity():
    rid = os.environ["GITHUB_RUN_ID"]
    if not rid.isdecimal():
        raise ValueError("INVALID_RUN_ID")
    return canonical_request_key(
        "SYNTHETIC_NO_FUGLE", "/no-paid-provider",
        {"contract": "redis_two_runner", "run_id": rid},
        "RESEARCH_NO_FUGLE", "PAPER_ONLY",
    )


def receipt_key(run_id: str, slot: str):
    if slot not in ("A", "B") or not run_id.isdecimal():
        raise ValueError("INVALID_RECEIPT_ID")
    return f"{PREFIX}:receipts:{run_id}:{slot}"


def write_local(obj, name):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def contender(slot):
    c = client()
    if not c.ping():
        raise ValueError("SHARED_REDIS_NOT_REACHABLE")
    rid = os.environ["GITHUB_RUN_ID"]
    key = identity()
    store = RedisAtomicStore(c, prefix=PREFIX)
    owner = f"{rid}:{slot}"
    decision = reserve(store, key, owner, "first-synthetic-attempt")
    if decision == "CALL_ONCE":
        result = json.dumps({
            "schema": "SKY_REDIS_CAS_SYNTHETIC_RESULT_V1",
            "run_id": rid, "request_key": key,
            "paid_provider_requests": 0,
            "synthetic": True, "automatic_order": False,
            "production_eligible": False,
        }, sort_keys=True).encode("utf-8")
        uri, digest = store.persist_research_result_if_absent(key, result)
        if not finalize_ready(store, key, owner, "first-synthetic-attempt",
                              uri, digest, quota_units=0, usage_source="NO_PROVIDER_CALL"):
            raise ValueError("SHARED_REDIS_READY_CAS_FAILED")
    elif decision not in ("BLOCK_IN_FLIGHT", "REUSE_READY"):
        raise ValueError("UNSAFE_RESERVATION:" + str(decision))
    receipt = {
        "schema": "SKY_REDIS_CAS_INDEPENDENT_CONTENDER_V1",
        "run_id": rid, "sha": os.environ["GITHUB_SHA"], "slot": slot,
        "owner_run_id": owner, "request_key": key,
        "decision": decision, "paid_provider_requests": 0,
        "synthetic": True, "automatic_order": False,
        "production_eligible": False, "trade_action": "禁止交易",
    }
    write_local(receipt, f"contender-{slot}.json")
    if c.set(receipt_key(rid, slot), json.dumps(receipt).encode(), nx=True) is not True:
        raise ValueError("DUPLICATE_CONTENDER_RECEIPT")
    print(json.dumps({"slot": slot, "decision": decision, "synthetic": True}))


def verify():
    c = client()
    if not c.ping():
        raise ValueError("SHARED_REDIS_NOT_REACHABLE")
    rid = os.environ["GITHUB_RUN_ID"]
    key = identity()
    store = RedisAtomicStore(c, prefix=PREFIX)
    rows = []
    for slot in ("A", "B"):
        raw = c.get(receipt_key(rid, slot))
        if not raw:
            raise ValueError("MISSING_INDEPENDENT_RUNNER_RECEIPT")
        d = json.loads(raw)
        if (d.get("run_id") != rid or d.get("sha") != os.environ["GITHUB_SHA"]
                or d.get("slot") != slot or d.get("request_key") != key
                or d.get("paid_provider_requests") != 0
                or d.get("synthetic") is not True
                or d.get("automatic_order") is not False
                or d.get("production_eligible") is not False):
            raise ValueError("INVALID_REMOTE_RUNNER_RECEIPT")
        rows.append(d)
    winners = [r for r in rows if r["decision"] == "CALL_ONCE"]
    losers = [r for r in rows if r["decision"] in ("BLOCK_IN_FLIGHT", "REUSE_READY")]
    if len(winners) != 1 or len(losers) != 1:
        raise ValueError("REDIS_CROSS_RUNNER_ATOMIC_CAS_FAILED")
    pair = store.read(key)
    if pair is None or pair[0].state != "READY":
        raise ValueError("SHARED_READY_NOT_PERSISTED")
    record, version = pair
    if (record.owner_run_id != winners[0]["owner_run_id"]
            or record.quota_units != 0
            or record.usage_source != "NO_PROVIDER_CALL"
            or store.verify_durable_result(record.result_uri, record.result_sha256) is not True):
        raise ValueError("SHARED_READY_RESULT_HASH_FAILED")
    if reserve(store, key, f"{rid}:verifier", "readback") != "REUSE_READY":
        raise ValueError("VERIFIER_MUST_REUSE_VERIFIED_RESULT")
    proof = {
        "schema": "SKY_REDIS_CAS_TWO_RUNNER_PROOF_V1",
        "status": "PASS_RESEARCH_ONLY", "run_id": rid,
        "sha": os.environ["GITHUB_SHA"], "request_key": key,
        "contender_slots": ["A", "B"], "call_once_count": 1,
        "blocked_or_reused_count": 1, "result_hash_verified": True,
        "redis_cas_revision": version,
        "cross_runner_remote_atomic_store_verified": True,
        "cross_workflow_runtime_lease_verified": False,
        "redis_restart_persistence_verified": False,
        "all_paid_entrypoints_wired": False,
        "paid_provider_requests": 0, "synthetic": True,
        "production_eligible": False, "automatic_order": False,
        "trade_action": "禁止交易",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_local(proof, "proof.json")
    print(json.dumps(proof, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("contender", "verify"), required=True)
    ap.add_argument("--slot", choices=("A", "B"))
    args = ap.parse_args()
    try:
        if args.mode == "contender":
            if not args.slot:
                raise ValueError("MISSING_CONTENDER_SLOT")
            contender(args.slot)
        else:
            verify()
    except Exception as exc:
        write_local({
            "schema": "SKY_REDIS_CAS_FAIL_CLOSED_V1", "status": "HOLD",
            "reason": type(exc).__name__ + ":" + str(exc)[:120],
            "paid_provider_requests": 0,
            "production_eligible": False, "automatic_order": False,
            "trade_action": "禁止交易",
        }, f"failure-{args.mode}{('-'+args.slot) if args.slot else ''}.json")
        raise


if __name__ == "__main__":
    main()
