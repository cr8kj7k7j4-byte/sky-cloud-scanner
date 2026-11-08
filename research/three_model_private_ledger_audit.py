"""Read-only private research ledger audit. NEVER expose paid prices or change GCS."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re

from research.three_model_next_session_markout import (
    OBS_PREFIX, OUTCOME_PREFIX, MAX_SCAN, MODEL_IDS, DIRECTIONS, validate_observation,
)
from research.three_model_fugle_pipeline import TPE

_ID = re.compile(r"[a-zA-Z0-9_-]{8,90}")
_SYMBOL = re.compile(r"[0-9]{4,5}")
_SHA = re.compile(r"[0-9a-f]{64}")


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError("missing_audited_timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamp_without_timezone")
    return parsed.astimezone(TPE).isoformat()


def read_only_audit(store, bucket, *, max_scan=MAX_SCAN):
    """Verify GCS object path, bytes, identity and paired markouts, never write."""
    if not isinstance(bucket, str) or not bucket or bucket == "sky-disclosure-evidence-20261108":
        raise ValueError("invalid_research_bucket")
    if not 1 <= max_scan <= MAX_SCAN:
        raise ValueError("invalid_scan_limit")
    observations = {}
    markouts = {}
    for prefix, destination in ((OBS_PREFIX, observations), (OUTCOME_PREFIX, markouts)):
        blobs = list(store.list_blobs(bucket, prefix=prefix, max_results=max_scan + 1))
        if len(blobs) > max_scan:
            raise ValueError("ledger_scan_limit_reached")
        for blob in blobs:
            name = blob.name
            if "/__preflight__/" in name:
                continue
            if not name.endswith(".json"):
                raise ValueError("unexpected_research_object")
            raw = blob.download_as_bytes()
            if not isinstance(raw, bytes):
                raise ValueError("invalid_gcs_object_bytes")
            digest = hashlib.sha256(raw).hexdigest()
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise ValueError("invalid_research_object")
            model, symbol, rid = (record.get("model_id"), record.get("symbol"),
                                  record.get("ledger_record_id"))
            if model not in MODEL_IDS or not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
                raise ValueError("invalid_research_model_or_symbol")
            if not isinstance(rid, str) or not _ID.fullmatch(rid):
                raise ValueError("invalid_research_record_id")
            expected = f"{prefix}{model}/{symbol}/{rid}.json"
            if name != expected:
                raise ValueError("research_object_path_mismatch")
            if rid in destination:
                raise ValueError("duplicate_research_record_id")
            if prefix == OBS_PREFIX:
                if record.get("signal_id") not in (None, rid):
                    raise ValueError("signal_ledger_id_mismatch")
                if record.get("data_source") not in (None, "FUGLE"):
                    raise ValueError("non_fugle_research_source")
                # validate_observation also blocks trade authorization flags.
                validated = validate_observation(record)
                if validated is None:
                    if not rid.startswith("rejected-"):
                        raise ValueError("missing_observation_evidence")
                    stamp = None
                else:
                    stamp = validated["bar_time"].isoformat()
                direction = record.get("direction")
                if direction not in DIRECTIONS:
                    raise ValueError("invalid_observation_direction")
                destination[rid] = {
                    "record_id": rid, "model_id": model, "symbol": symbol,
                    "direction": direction, "bar_time_tpe": stamp,
                    "object_sha256": digest, "object_path": name,
                }
            else:
                if record.get("schema") != "sky-three-model-next-session-markout-v1":
                    raise ValueError("invalid_markout_schema")
                if any(record.get(k) is not False for k in
                       ("actual_fill", "trade_eligible", "production_signal", "trading_enabled")):
                    raise ValueError("unsafe_markout_claim")
                if record.get("realized_net_pnl") is not None or record.get("net_strategy_return") is not None:
                    raise ValueError("unsafe_markout_pnl")
                direction = record.get("direction_at_observation")
                if direction not in DIRECTIONS:
                    raise ValueError("invalid_markout_direction")
                observation_time = _stamp(record.get("observation_bar_time"))
                next_time = _stamp(record.get("next_session_close_time"))
                if next_time[:10] <= observation_time[:10]:
                    raise ValueError("non_future_markout_session")
                destination[rid] = {
                    "record_id": rid, "model_id": model, "symbol": symbol,
                    "direction": direction, "observation_bar_time_tpe": observation_time,
                    "next_session_close_time_tpe": next_time,
                    "object_sha256": digest, "object_path": name,
                }
    # An orphan follow-up is a stronger evidence-integrity failure than an
    # empty bucket. Preserve its explicit error instead of masking it.
    if not observations and not markouts:
        raise ValueError("no_research_observations_found")
    for rid, row in markouts.items():
        source = observations.get(rid)
        if source is None:
            raise ValueError("orphan_markout_record")
        if source["bar_time_tpe"] is None:
            raise ValueError("markout_references_rejected_observation")
        if any((row["model_id"] != source["model_id"],
                row["symbol"] != source["symbol"],
                row["direction"] != source["direction"],
                row["observation_bar_time_tpe"] != source["bar_time_tpe"])):
            raise ValueError("markout_observation_identity_mismatch")
    return {
        "status": "PRIVATE_LEDGER_READ_ONLY_AUDIT",
        "source": "private_gcs_existing_objects",
        "observations_scanned": len(observations),
        "markouts_scanned": len(markouts),
        "markouts_linked_to_original": len(markouts),
        "pending_observations": len(observations) - len(markouts),
        "observations": sorted(observations.values(), key=lambda x: (x["model_id"], x["symbol"], x["record_id"])),
        "markouts": sorted(markouts.values(), key=lambda x: (x["model_id"], x["symbol"], x["record_id"])),
        "raw_paid_ohlcv_exported": False,
        "writes_performed": False,
        "trained_ai_inference_verified": False,
        "production_signal": False,
        "trading_enabled": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default=os.environ.get("SKY_RESEARCH_GCS_BUCKET", ""))
    parser.add_argument("--out", default="output/three_model_private_ledger_audit.json")
    args = parser.parse_args()
    if not args.bucket:
        raise ValueError("missing_private_research_bucket")
    from google.cloud import storage
    report = read_only_audit(storage.Client(), args.bucket)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"],
                      "observations_scanned": report["observations_scanned"],
                      "markouts_scanned": report["markouts_scanned"],
                      "trading_enabled": False}))


if __name__ == "__main__":
    main()
