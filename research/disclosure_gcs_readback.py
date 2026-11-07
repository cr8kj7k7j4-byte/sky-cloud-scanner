"""Fail-closed write-once GCS evidence upload with byte-for-byte readback.

Writes only official source snapshots from a verified local manifest; does not
claim original event publication time or perform trading. Cloud object retention
policy and authorized storage account must be reviewed separately.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ("twse_revenue_latest", "tpex_revenue_latest",
            "twse_material_latest", "tpex_material_latest")
SOURCE_NAMES = frozenset(REQUIRED)
RUN_ID_RE = re.compile(r"^[0-9]{5,20}$")
ATTEMPT_RE = re.compile(r"^[0-9]{1,3}$")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_capture(folder: Path):
    path = folder / "manifest.json"
    manifest_raw = path.read_bytes()
    manifest = json.loads(manifest_raw)
    if (manifest.get("status") != "SNAPSHOT_CAPTURED_RESEARCH_ONLY"
            or manifest.get("production_signal") is not False
            or manifest.get("historical_pit_event_count") != 0
            or set(manifest.get("source_results", {})) != SOURCE_NAMES):
        raise ValueError("invalid manifest or data incomplete")
    objects = {}
    for name in REQUIRED:
        spec = manifest["source_results"][name]
        if (spec.get("fetch_status") != "CAPTURED"
                or spec.get("http_status") != 200
                or spec.get("raw_file") != f"{name}.raw.json"):
            raise ValueError("missing or invalid source " + name)
        raw = (folder / spec["raw_file"]).read_bytes()
        if digest(raw) != spec.get("sha256") or len(raw) != spec.get("bytes"):
            raise ValueError("source hash or byte count mismatch " + name)
        if not spec.get("observed_at_utc"):
            raise ValueError("missing observed_at time " + name)
        objects[spec["raw_file"]] = raw
    objects["manifest.json"] = manifest_raw
    return objects


def object_prefix(run_id, attempt):
    if not RUN_ID_RE.fullmatch(run_id or "") or not ATTEMPT_RE.fullmatch(attempt or ""):
        raise ValueError("valid run id and attempt required")
    # Unique name per GitHub run and attempt, not mutable daily/latest object.
    return "disclosure-forward/v1/run-" + run_id + "-attempt-" + attempt


def upload_and_verify(folder: Path, bucket, prefix: str):
    """Bucket is injectable for no-network tests. Do not overwrite old evidence."""
    objects = validate_capture(folder)
    # Put manifest LAST as commit marker, after exact readback of every raw object.
    report = {"state": "GCS_READBACK_VERIFIED",
              "production_signal": False,
              "historical_pit_event_count": 0,
              "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "prefix": prefix, "objects": {}}
    for name in [*REQUIRED]:
        obj_name = f"{prefix}/{name}.raw.json"
        blob = bucket.blob(obj_name)
        content = objects[name + ".raw.json"]
        blob.upload_from_string(content, content_type="application/json",
                                if_generation_match=0)
        fetched = blob.download_as_bytes()
        if fetched != content or digest(fetched) != digest(content):
            raise ValueError("GCS RAW READBACK HASH MISMATCH " + name)
        report["objects"][name] = {"sha256": digest(content),
                                    "bytes": len(content),
                                    "readback_verified": True}
    manifest_blob = bucket.blob(prefix + "/manifest.json")
    manifest_blob.upload_from_string(objects["manifest.json"],
                                     content_type="application/json",
                                     if_generation_match=0)
    read_manifest = manifest_blob.download_as_bytes()
    if read_manifest != objects["manifest.json"]:
        raise ValueError("GCS MANIFEST READBACK MISMATCH")
    report["manifest_sha256"] = digest(read_manifest)
    report["gcs_bucket_retention_policy_verified"] = False
    report["gcs_iam_least_privilege_verified"] = False
    report["immutable_gcs_bucket_policy_verified"] = False
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default="research_output/disclosure_forward_snapshot")
    ap.add_argument("--receipt", default="research_output/gcs_readback_receipt.json")
    args = ap.parse_args()
    name = os.environ.get("DISCLOSURE_GCS_BUCKET", "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,61}[a-z0-9]", name):
        raise SystemExit("GCS_BUCKET_UNCONFIGURED_OR_INVALID")
    prefix = object_prefix(os.environ.get("GITHUB_RUN_ID", ""),
                           os.environ.get("GITHUB_RUN_ATTEMPT", ""))
    try:
        from google.cloud import storage
        bucket = storage.Client().bucket(name)
    except ImportError:
        raise SystemExit("GOOGLE_CLOUD_STORAGE_LIBRARY_MISSING")
    result = upload_and_verify(Path(args.folder), bucket, prefix)
    out = Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"state": result["state"], "prefix": prefix,
                      "readback_sources": len(result["objects"]),
                      "production_signal": False,
                      "bucket_retention_verified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
