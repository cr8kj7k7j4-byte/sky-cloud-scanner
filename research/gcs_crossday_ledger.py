"""Rebuild a forward-only, immutable event ledger from GCS evidence snapshots.

Every GCS snapshot is independently SHA-verified before ingestion. No existing
object is updated, and first-observed never becomes original issuer publication.
Historical revenue replay stays blocked until independent event PIT proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from research.disclosure_gcs_readback import REQUIRED
from research.forward_event_ledger import build_ledger
from research.gcs_post_upload_integrity_audit import (
    PREFIX, MAX_OBJECT_BYTES, audit_snapshot, select_latest_completed_prefix
)

LEDGER_PREFIX = "disclosure-forward-ledgers/v1"
MAX_EVIDENCE_BATCHES = 300
RUN_RE = re.compile(r"^[0-9]{5,20}$")
ATTEMPT_RE = re.compile(r"^[0-9]{1,3}$")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def get_completed_prefixes(bucket):
    names = [obj.name for obj in bucket.list_blobs(prefix=PREFIX)]
    sorted_latest = select_latest_completed_prefix(names)
    # IMPORTANT: The existing helper truncates at 30 by default. Refuse to
    # silently drop older batches; independently check actual manifest count.
    all_manifests = {
        name for name in names
        if name.startswith(PREFIX) and name.endswith("/manifest.json")
        and name.count("/") == 3
    }
    if len(all_manifests) > MAX_EVIDENCE_BATCHES:
        raise ValueError("EXCESS_EVIDENCE_BATCHES_REQUIRES_CHECKPOINT_DESIGN")
    def run_key(path):
        tail = path[:-len("/manifest.json")].split("/")[-1]
        match = re.fullmatch(r"run-([0-9]+)-attempt-([0-9]+)", tail)
        if not match:
            raise ValueError("INVALID_MANIFEST_PATH")
        return int(match.group(1)), int(match.group(2))
    if not all_manifests:
        raise ValueError("NO_COMMITTED_SNAPSHOTS")
    return [key[:-len("/manifest.json")] for key in sorted(all_manifests, key=run_key)]


def build_crossday(bucket):
    prefixes = get_completed_prefixes(bucket)
    ledger = None
    lineage = []
    total = {"added": 0, "unchanged": 0, "revision": 0,
             "skipped_invalid": 0, "duplicate_rows_within_snapshot": 0}
    previous_observed = None
    for prefix in prefixes:
        result = audit_snapshot(bucket, prefix)
        if result["verified_object_count"] != 5:
            raise ValueError("INVALID_GCS_SNAPSHOT")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for source in REQUIRED:
                payload = bucket.blob(prefix + "/" + source + ".raw.json").download_as_bytes()
                if len(payload) > MAX_OBJECT_BYTES:
                    raise ValueError("OVERSIZED_EVIDENCE")
                (folder / (source + ".raw.json")).write_bytes(payload)
            manifest = bucket.blob(prefix + "/manifest.json").download_as_bytes()
            (folder / "manifest.json").write_bytes(manifest)
            doc = json.loads(manifest)
            ts_list = [datetime.fromisoformat(doc["source_results"][k]["observed_at_utc"].replace("Z","+00:00"))
                       for k in REQUIRED]
            if any(tz.utcoffset() is None for tz in ts_list):
                raise ValueError("MISSING_SOURCE_TIMEZONE")
            earliest = min(ts_list)
            if previous_observed is not None and earliest < previous_observed:
                raise ValueError("NON_MONOTONIC_EVIDENCE_OBSERVATION")
            previous_observed = max(ts_list)
            ledger = build_ledger(folder, ledger)
            for key in total:
                total[key] += ledger["counts"][key]
            lineage.append({"prefix": prefix, "manifest_sha256": sha(manifest),
                            "min_observed_at_utc": earliest.isoformat(),
                            "max_observed_at_utc": previous_observed.isoformat()})
    if not ledger or len(lineage) != len(prefixes):
        raise ValueError("UNEXPECTED_EMPTY_LEDGER")
    ledger["snapshot_batches"] = len(lineage)
    ledger["snapshot_lineage"] = lineage
    ledger["cumulative_counts"] = total
    ledger["status"] = "OBSERVED_ONLY_NOT_PIT_ELIGIBLE"
    ledger["eligible_trade_events"] = 0
    ledger["historical_pit_certified"] = False
    ledger["production_signal"] = False
    return ledger


def immutable_commit(bucket, ledger, run_id, attempt):
    if not RUN_RE.fullmatch(run_id or "") or not ATTEMPT_RE.fullmatch(attempt or ""):
        raise ValueError("INVALID_GITHUB_RUN_CONTEXT")
    path = f"{LEDGER_PREFIX}/run-{run_id}-attempt-{attempt}/ledger.json"
    raw = json.dumps(ledger, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    blob = bucket.blob(path)
    blob.upload_from_string(raw, content_type="application/json", if_generation_match=0)
    read = blob.download_as_bytes()
    if read != raw or sha(read) != sha(raw):
        raise ValueError("LEDGER_GCS_READBACK_FAILED")
    return {"status": "GCS_CROSSDAY_LEDGER_READBACK_PASS",
            "object_path": path, "sha256": sha(raw), "bytes": len(raw),
            "source_batches": ledger["snapshot_batches"],
            "unique_provisional_events": ledger["unique_provisional_events"],
            "cumulative_counts": ledger["cumulative_counts"],
            "issuer_original_published_at_verified": False,
            "eligible_trade_events": 0,
            "production_signal": False,
            "retention_iam_gate": "NOT_VERIFIED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", default="research_output/gcs_crossday_ledger_receipt.json")
    args = parser.parse_args()
    name = os.getenv("DISCLOSURE_GCS_BUCKET")
    if not name:
        raise SystemExit("GCS_BUCKET_UNCONFIGURED")
    from google.cloud import storage
    bucket = storage.Client().bucket(name)
    ledger = build_crossday(bucket)
    report = immutable_commit(bucket, ledger,
                              os.getenv("GITHUB_RUN_ID", ""),
                              os.getenv("GITHUB_RUN_ATTEMPT", ""))
    out = Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
