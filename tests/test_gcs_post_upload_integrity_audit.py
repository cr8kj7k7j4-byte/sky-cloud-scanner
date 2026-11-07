import hashlib
import json
import unittest

from research.gcs_post_upload_integrity_audit import (
    audit_bucket, audit_snapshot, select_latest_completed_prefix
)
from research.disclosure_gcs_readback import REQUIRED


class FakeObject:
    def __init__(self, name, content=None):
        self.name = name
        self.content = content
    def download_as_bytes(self):
        return self.content


class FakeBucket:
    def __init__(self, objects, metadata_allowed=True):
        self.objects = objects
        self.metadata_allowed = metadata_allowed
    def blob(self, key):
        if key not in self.objects:
            raise FileNotFoundError(key)
        return FakeObject(key, self.objects[key])
    def list_blobs(self, prefix):
        return [FakeObject(key) for key in self.objects if key.startswith(prefix)]
    def reload(self):
        if not self.metadata_allowed:
            raise PermissionError("storage.buckets.get unavailable")
        self.retention_policy = None
        self.versioning_enabled = False
        self.public_access_prevention = "enforced"
        self.uniform_bucket_level_access_enabled = True


def make_bucket(prefix="disclosure-forward/v1/run-42419000000-attempt-1"):
    objects = {}
    entries = {}
    for src in REQUIRED:
        raw = json.dumps([{"stock_id":"1101","source":src}], sort_keys=True).encode()
        objects[prefix + "/" + src + ".raw.json"] = raw
        entries[src] = {
            "fetch_status": "CAPTURED", "http_status": 200,
            "raw_file": src + ".raw.json",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "observed_at_utc": "2026-11-08T01:00:00+00:00"
        }
    manifest = {"status": "SNAPSHOT_CAPTURED_RESEARCH_ONLY",
                "production_signal": False, "historical_pit_event_count": 0,
                "source_results": entries}
    objects[prefix + "/manifest.json"] = json.dumps(manifest).encode()
    return FakeBucket(objects), prefix


class GCSAuditTests(unittest.TestCase):
    def test_five_original_objects_readback(self):
        bucket, prefix = make_bucket()
        result = audit_snapshot(bucket, prefix)
        self.assertEqual(result["verdict"], "PASS_5_OBJECTS_READBACK")
        self.assertEqual(result["verified_object_count"], 5)
        self.assertTrue(result["manifest_readback_verified"])

    def test_hash_tampering_rejected(self):
        bucket, prefix = make_bucket()
        bucket.objects[prefix + "/" + REQUIRED[0] + ".raw.json"] = b"tampered"
        with self.assertRaisesRegex(ValueError, "mismatch"):
            audit_snapshot(bucket, prefix)

    def test_manifest_missing_not_complete(self):
        bucket, prefix = make_bucket()
        del bucket.objects[prefix + "/manifest.json"]
        result = audit_bucket(bucket)
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertFalse(result["production_signal"])

    def test_latest_numeric_run_chosen(self):
        a="disclosure-forward/v1/run-99999-attempt-1/manifest.json"
        b="disclosure-forward/v1/run-100000-attempt-1/manifest.json"
        self.assertEqual(select_latest_completed_prefix([a,b])[0],
                         "disclosure-forward/v1/run-100000-attempt-1")

    def test_missing_bucket_meta_is_not_false_pass(self):
        bucket, _ = make_bucket()
        bucket.metadata_allowed = False
        result = audit_bucket(bucket)
        self.assertEqual(result["status"], "GCS_5_OBJECT_READBACK_PASS_POLICY_REVIEW_PENDING")
        self.assertEqual(result["bucket_policy"]["bucket_metadata_access"], "NO_PERMISSION_OR_UNAVAILABLE")
        self.assertFalse(result["bucket_policy"]["durable_immutability_verified"])

    def test_valid_bucket_metadata_not_retention_pass(self):
        bucket, _ = make_bucket()
        result = audit_bucket(bucket)
        self.assertEqual(result["bucket_policy"]["bucket_metadata_access"], "READABLE")
        self.assertFalse(result["bucket_policy"]["durable_immutability_verified"])
        self.assertFalse(result["production_signal"])


if __name__ == "__main__":
    unittest.main()
