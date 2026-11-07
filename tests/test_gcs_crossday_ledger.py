import hashlib
import json
import unittest

from research.disclosure_gcs_readback import REQUIRED
from research.gcs_crossday_ledger import (
    build_crossday, get_completed_prefixes, immutable_commit
)


class Blob:
    def __init__(self, db, path):
        self.db, self.path = db, path
        self.name = path
    def download_as_bytes(self):
        return self.db[self.path]
    def upload_from_string(self, data, content_type, if_generation_match):
        assert if_generation_match == 0
        if self.path in self.db:
            raise ValueError("overwrite denied")
        self.db[self.path] = data


class Bucket:
    def __init__(self, db):
        self.db = db
    def blob(self, path):
        return Blob(self.db, path)
    def list_blobs(self, prefix):
        return [Blob(self.db, p) for p in self.db if p.startswith(prefix)]


def seed(db, run, value, minute, include_manifest=True):
    prefix = f"disclosure-forward/v1/run-{run}-attempt-1"
    source_results = {}
    for source in REQUIRED:
        if "revenue" in source:
            rows = [{"公司代號": "1101" if source.startswith("twse") else "8088",
                     "資料年月": "11510", "當月營收": value}]
        else:
            rows = [{"公司代號": "1101" if source.startswith("twse") else "8088",
                     "主旨": "重大訊息", "發言日期": "1151108",
                     "發言時間": "10:00", "說明": value}]
        raw = json.dumps(rows, ensure_ascii=False).encode()
        db[prefix + "/" + source + ".raw.json"] = raw
        source_results[source] = {
            "http_status": 200, "fetch_status": "CAPTURED",
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "raw_file": source + ".raw.json",
            "observed_at_utc": f"2026-11-08T02:{minute:02d}:00+00:00"
        }
    if include_manifest:
        doc = {"status": "SNAPSHOT_CAPTURED_RESEARCH_ONLY",
               "production_signal": False, "historical_pit_event_count": 0,
               "source_results": source_results}
        db[prefix + "/manifest.json"] = json.dumps(doc).encode()
    return prefix


class TestCrossdayLedger(unittest.TestCase):
    def test_same_snapshot_idempotent_and_changed_revision(self):
        db = {}
        seed(db, "42419000000", "100", 0)
        seed(db, "42419000001", "100", 2)
        seed(db, "42419000002", "200", 4)
        ledger = build_crossday(Bucket(db))
        self.assertEqual(ledger["snapshot_batches"], 3)
        self.assertEqual(ledger["unique_provisional_events"], 4)
        self.assertEqual(ledger["cumulative_counts"]["added"], 4)
        self.assertEqual(ledger["cumulative_counts"]["unchanged"], 4)
        self.assertEqual(ledger["cumulative_counts"]["revision"], 4)
        self.assertEqual(ledger["eligible_trade_events"], 0)
        self.assertFalse(ledger["historical_pit_certified"])

    def test_commit_create_only_and_readback(self):
        db = {}
        seed(db, "42419000000", "100", 0)
        bucket = Bucket(db)
        ledger = build_crossday(bucket)
        report = immutable_commit(bucket, ledger, "42419000009", "1")
        self.assertEqual(report["status"], "GCS_CROSSDAY_LEDGER_READBACK_PASS")
        self.assertEqual(report["eligible_trade_events"], 0)
        self.assertIn(report["object_path"], db)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            immutable_commit(bucket, ledger, "42419000009", "1")

    def test_tampered_source_fails_closed(self):
        db = {}
        prefix = seed(db, "42419000000", "100", 0)
        db[prefix + "/" + REQUIRED[0] + ".raw.json"] = b"changed"
        with self.assertRaisesRegex(ValueError, "mismatch"):
            build_crossday(Bucket(db))

    def test_uncommitted_raw_snapshot_ignored(self):
        db = {}
        seed(db, "42419000000", "100", 0)
        seed(db, "42419000001", "200", 2, include_manifest=False)
        self.assertEqual(len(get_completed_prefixes(Bucket(db))), 1)

    def test_out_of_order_observation_rejected(self):
        db = {}
        seed(db, "42419000000", "100", 4)
        seed(db, "42419000001", "200", 0)
        with self.assertRaisesRegex(ValueError, "NON_MONOTONIC"):
            build_crossday(Bucket(db))

    def test_missing_committed_manifest_fails_closed(self):
        db = {}
        with self.assertRaisesRegex(ValueError, "NO_COMMITTED"):
            build_crossday(Bucket(db))


if __name__ == "__main__":
    unittest.main()
