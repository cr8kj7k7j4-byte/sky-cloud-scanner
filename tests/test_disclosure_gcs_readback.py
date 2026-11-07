import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from research.disclosure_gcs_readback import (
    REQUIRED, object_prefix, upload_and_verify, validate_capture
)


class FakeBlob:
    def __init__(self, store, name):
        self.store, self.name = store, name
    def upload_from_string(self, body, content_type, if_generation_match):
        assert if_generation_match == 0
        if self.name in self.store: raise ValueError("overwrite blocked")
        self.store[self.name] = body
    def download_as_bytes(self):
        return self.store[self.name]


class FakeBucket:
    def __init__(self):
        self.store = {}
    def blob(self, name):
        return FakeBlob(self.store, name)


def populate(folder):
    folder.mkdir(parents=True, exist_ok=True)
    sources = {}
    for name in REQUIRED:
        body = json.dumps([{"symbol": name}], ensure_ascii=False).encode()
        (folder / f"{name}.raw.json").write_bytes(body)
        sources[name] = {
            "fetch_status": "CAPTURED", "http_status": 200,
            "raw_file": name + ".raw.json",
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "observed_at_utc": "2026-11-08T00:00:00+00:00",
        }
    record = {"status": "SNAPSHOT_CAPTURED_RESEARCH_ONLY",
              "production_signal": False,
              "historical_pit_event_count": 0,
              "source_results": sources}
    (folder / "manifest.json").write_text(json.dumps(record))


class StorageTests(unittest.TestCase):
    def test_exact_readback_and_non_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); populate(folder)
            bucket = FakeBucket()
            report = upload_and_verify(folder, bucket, object_prefix("42417888034", "1"))
            self.assertEqual(len(report["objects"]), 4)
            self.assertEqual(len(bucket.store), 5)
            self.assertTrue(all(row["readback_verified"] for row in report["objects"].values()))
            self.assertFalse(report["production_signal"])
            self.assertFalse(report["immutable_gcs_bucket_policy_verified"])
            with self.assertRaises(ValueError):
                upload_and_verify(folder, bucket, object_prefix("42417888034", "1"))

    def test_rejects_tampered_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); populate(folder)
            (folder / "twse_revenue_latest.raw.json").write_bytes(b"tamper")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                validate_capture(folder)

    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); populate(folder)
            (folder / "tpex_material_latest.raw.json").unlink()
            with self.assertRaises(FileNotFoundError):
                validate_capture(folder)

    def test_incomplete_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); populate(folder)
            data = json.loads((folder / "manifest.json").read_text())
            data["status"] = "INCOMPLETE_DATA"
            (folder / "manifest.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                validate_capture(folder)

    def test_invalid_run_id_rejected(self):
        for value in ("", "../../etc", "abc", "0"):
            with self.assertRaises(ValueError):
                object_prefix(value, "1")


if __name__ == "__main__":
    unittest.main()
