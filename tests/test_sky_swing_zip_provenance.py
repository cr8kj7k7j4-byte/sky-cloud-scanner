"""W0 #363: offline real ZIP byte hashing and defensive extraction tests."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from src.sky_swing_zip_provenance import read_verified_swing_zips

SHA = "a" * 40
NOW = datetime(2026, 11, 27, tzinfo=timezone.utc)


def zipped(root, name, files, artifact_id):
    archive = root / name
    with ZipFile(archive, "w") as z:
        for path, content in files.items():
            z.writestr(path, content)
    return archive, {
        "id": artifact_id,
        "name": name.split(".zip")[0],
        "expired": False,
        "digest": "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest(),
    }


class HistoricalSwingZipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        receipt = {
            "status": "PASS_ARTIFACT_INTEGRITY_RESEARCH_ONLY",
            "run_id": "123", "head_sha": SHA, "mode": "swing",
            "artifact_name": "sky-swing-live-123", "artifact_id": 321,
            "data_timestamp": "2026-11-26T14:00:00+08:00",
        }
        self.source, self.src_meta = zipped(
            self.root, "sky-swing-live-123.zip",
            {"latest_swing.json": "{}", "snapshot_observations_swing.json": "{}",
             "two_track_acceptance.json": "{}"}, 321,
        )
        self.readback, self.rb_meta = zipped(
            self.root, "sky-swing-readback-123.zip",
            {"receipt.json": json.dumps(receipt)}, 322,
        )

    def check(self, **overrides):
        kwargs = {
            "source_zip": self.source,
            "source_metadata": self.src_meta,
            "readback_zip": self.readback,
            "readback_metadata": self.rb_meta,
            "expected_run_id": "123",
            "expected_head_sha": SHA,
            "observed_at": NOW,
        }
        return read_verified_swing_zips(**{**kwargs, **overrides})

    def test_verified_zip_digest_and_receipt_binding_reaches_existing_reader(self):
        with patch("src.sky_swing_zip_provenance.read_historical_observation") as reader:
            reader.return_value = {
                "status": "PASS_HISTORICAL_RESEARCH_OBSERVATION_ONLY",
                "text": "研究觀察", "new_entry_authorized": False,
            }
            result = self.check()
            self.assertEqual(result["status"], "PASS_ZIP_BYTES_AND_RESEARCH_OBSERVATION_ONLY")
            self.assertFalse(result["github_run_metadata_certified"])
            self.assertFalse(result["new_entry_authorized"])
            reader.assert_called_once()

    def test_tampered_zip_bytes_rejected(self):
        with self.source.open("ab") as f:
            f.write(b"tamper")
        result = self.check()
        self.assertEqual(result["reason"], "GITHUB_ARTIFACT_DIGEST_MISMATCH")

    def test_wrong_artifact_name_rejected(self):
        result = self.check(source_metadata={**self.src_meta, "name": "sky-swing-live-999"})
        self.assertEqual(result["reason"], "GITHUB_ARTIFACT_METADATA_INVALID")

    def test_unsafe_member_rejected(self):
        malicious, metadata = zipped(self.root, "malicious.zip",
                                      {"../escape.json": "bad"}, 444)
        metadata["name"] = "sky-swing-live-123"
        result = self.check(source_zip=malicious, source_metadata=metadata)
        self.assertEqual(result["reason"], "ARTIFACT_UNSAFE_MEMBER")
        self.assertFalse((self.root / "escape.json").exists())

    def test_5d_receipt_cannot_replace_swing_receipt(self):
        with ZipFile(self.readback, "w") as z:
            z.writestr("receipt.json", json.dumps({
                "status": "PASS_ARTIFACT_INTEGRITY_RESEARCH_ONLY",
                "run_id": "123", "head_sha": SHA, "mode": "swing5d",
                "artifact_name": "sky-swing-live-123", "artifact_id": 321,
            }))
        metadata = {**self.rb_meta,
                    "digest": "sha256:" + hashlib.sha256(self.readback.read_bytes()).hexdigest()}
        result = self.check(readback_metadata=metadata)
        self.assertEqual(result["status"], "HOLD_EVIDENCE")

    def test_forged_source_artifact_id_rejected(self):
        with patch("src.sky_swing_zip_provenance.read_historical_observation") as reader:
            reader.return_value = {
                "status": "PASS_HISTORICAL_RESEARCH_OBSERVATION_ONLY",
                "text": "觀察",
            }
            result = self.check(source_metadata={**self.src_meta, "id": 999})
            self.assertEqual(result["reason"], "RECEIPT_ARTIFACT_ID_MISMATCH")


if __name__ == "__main__":
    unittest.main()
