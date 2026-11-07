"""Read-only GCS post-upload audit for official disclosure evidence.

No downloads of paid Fugle feeds, no writes, no trading instructions.
Only checks the latest completed snapshot within the dedicated evidence prefix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from research.disclosure_gcs_readback import REQUIRED

PREFIX = "disclosure-forward/v1/"
MAX_OBJECT_BYTES = 15_000_000
MAX_SNAPSHOTS_TO_EXAMINE = 30


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit_snapshot(bucket, prefix: str):
    """Independently re-read original 5 stored objects, verify hash and manifest."""
    if not prefix.startswith(PREFIX) or ".." in prefix or not prefix.rstrip("/").split("/")[-1].startswith("run-"):
        raise ValueError("unsupported evidence prefix")
    report = {"prefix": prefix, "verdict": "FAIL", "files": {},
              "revenue_event_pit_verified": False, "production_signal": False}
    manifest_blob = bucket.blob(prefix + "/manifest.json")
    manifest_bytes = manifest_blob.download_as_bytes()
    if len(manifest_bytes) > MAX_OBJECT_BYTES:
        raise ValueError("manifest too large")
    doc = json.loads(manifest_bytes.decode("utf-8"))
    if (doc.get("status") != "SNAPSHOT_CAPTURED_RESEARCH_ONLY"
            or doc.get("production_signal") is not False
            or doc.get("historical_pit_event_count") != 0
            or set(doc.get("source_results", {})) != set(REQUIRED)):
        raise ValueError("manifest contract invalid")
    for src in REQUIRED:
        entry = doc["source_results"][src]
        if entry.get("fetch_status") != "CAPTURED" or entry.get("http_status") != 200 or entry.get("raw_file") != src + ".raw.json":
            raise ValueError("source incomplete: " + src)
        raw = bucket.blob(prefix + "/" + src + ".raw.json").download_as_bytes()
        if len(raw) > MAX_OBJECT_BYTES:
            raise ValueError("oversized source " + src)
        if sha(raw) != entry.get("sha256") or len(raw) != entry.get("bytes"):
            raise ValueError("source readback mismatch " + src)
        report["files"][src] = {
            "sha256": sha(raw), "bytes": len(raw), "readback_verified": True,
            "first_observed_at_utc": entry.get("observed_at_utc"),
        }
    report["manifest_sha256"] = sha(manifest_bytes)
    report["manifest_readback_verified"] = True
    report["verified_object_count"] = len(REQUIRED) + 1
    report["verdict"] = "PASS_5_OBJECTS_READBACK"
    return report


def select_latest_completed_prefix(blob_names):
    candidates = sorted({
        name[: -len("/manifest.json")]
        for name in blob_names
        if name.startswith(PREFIX) and name.endswith("/manifest.json")
        and name.count("/") == 3
    }, reverse=True)
    # Lexicographic sort by numeric GitHub run id is not guaranteed across widths.
    def extract_run(prefix):
        last = prefix.split("/")[-1]
        try:
            run, attempt = last.removeprefix("run-").split("-attempt-")
            return int(run), int(attempt)
        except (ValueError, TypeError):
            return -1, -1
    candidates.sort(key=extract_run, reverse=True)
    return candidates[:MAX_SNAPSHOTS_TO_EXAMINE]


def inspect_bucket_policy(bucket):
    """Do not confuse metadata permission failure with verified insecure policy."""
    outcome = {
        "bucket_metadata_access": "NOT_VERIFIED",
        "retention_policy_seconds": None,
        "retention_policy_locked": None,
        "versioning_enabled": None,
        "public_access_prevention": None,
        "uniform_access_enabled": None,
        "iam_policy_review": "NOT_VERIFIED_SEPARATE_CONSOLE_REVIEW_REQUIRED",
        "durable_immutability_verified": False,
    }
    try:
        bucket.reload()
        outcome["bucket_metadata_access"] = "READABLE"
        policy = getattr(bucket, "retention_policy", None)
        outcome["retention_policy_seconds"] = policy.get("retentionPeriod") if isinstance(policy, dict) else None
        outcome["retention_policy_locked"] = policy.get("isLocked") if isinstance(policy, dict) else None
        outcome["versioning_enabled"] = getattr(bucket, "versioning_enabled", None)
        outcome["public_access_prevention"] = getattr(bucket, "public_access_prevention", None)
        outcome["uniform_access_enabled"] = getattr(bucket, "uniform_bucket_level_access_enabled", None)
    except Exception as exc:
        # IAM policy and retention must be verified by an admin on the console.
        outcome["bucket_metadata_access"] = "NO_PERMISSION_OR_UNAVAILABLE"
        outcome["metadata_error_type"] = type(exc).__name__
    return outcome


def audit_bucket(bucket):
    # Listing metadata only. No object writes or deletes.
    names = [b.name for b in bucket.list_blobs(prefix=PREFIX)]
    prefixes = select_latest_completed_prefix(names)
    out = {
        "model": "GCS_POST_UPLOAD_INTEGRITY_AUDIT_V1",
        "audit_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "INSUFFICIENT_DATA",
        "production_signal": False,
        "number_of_completed_prefixes_seen": len(prefixes),
        "audited_prefix": None,
        "object_audit": None,
        "bucket_policy": inspect_bucket_policy(bucket),
        "issuer_original_published_at_verified": False,
        "strategy_positive_expectancy_verified": False,
    }
    if not prefixes:
        out["blocked_reason"] = "NO_COMMITTED_MANIFEST_FOUND"
        return out
    prefix = prefixes[0]
    out["audited_prefix"] = prefix
    out["object_audit"] = audit_snapshot(bucket, prefix)
    out["status"] = "GCS_5_OBJECT_READBACK_PASS_POLICY_REVIEW_PENDING"
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="research_output/gcs_post_upload_integrity_audit.json")
    args = parser.parse_args()
    bucket_name = os.getenv("DISCLOSURE_GCS_BUCKET", "").strip()
    if not bucket_name:
        raise SystemExit("GCS_BUCKET_UNCONFIGURED")
    from google.cloud import storage
    output = audit_bucket(storage.Client().bucket(bucket_name))
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": output["status"], "audited_prefix": output["audited_prefix"],
        "verified_object_count": (output["object_audit"] or {}).get("verified_object_count", 0),
        "bucket_metadata_access": output["bucket_policy"]["bucket_metadata_access"],
        "retention_policy_seconds": output["bucket_policy"]["retention_policy_seconds"],
        "iam_policy_review": output["bucket_policy"]["iam_policy_review"],
        "production_signal": False,
    }, ensure_ascii=False))
    if output["status"] != "GCS_5_OBJECT_READBACK_PASS_POLICY_REVIEW_PENDING":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
