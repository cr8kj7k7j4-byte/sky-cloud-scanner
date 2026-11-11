"""No-provider deterministic contract tests for #515. No paid Fugle calls."""
import hashlib
import threading
import unittest
from dataclasses import replace

from research.sky_paid_api_dedup_contract import (
    canonical_request_key, reserve, finalize_ready, quarantine_uncertain
)


class SharedMockStore:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()
        self.persisted_results = {}
    def write_result(self, uri, data):
        self.persisted_results[uri] = bytes(data)
    def verify_durable_result(self, uri, digest):
        data = self.persisted_results.get(uri)
        return data is not None and hashlib.sha256(data).hexdigest() == digest
    def create_if_absent(self, key, record):
        with self.lock:
            if key in self.data:
                return False
            self.data[key] = (record, 1)
            return True
    def read(self, key):
        with self.lock:
            entry = self.data.get(key)
            return (entry[0], str(entry[1])) if entry else None
    def compare_and_swap(self, key, version, record):
        with self.lock:
            old = self.data.get(key)
            if old is None or str(old[1]) != version:
                return False
            self.data[key] = (record, old[1] + 1)
            return True


def key():
    return canonical_request_key("FUGLE", "/quote", {"symbols": ["1101", "8088"]},
                                 "entitlement-A", "2026-11-11T09:00+08:00")


class ContractTests(unittest.TestCase):
    def test_identity_is_order_independent_and_different_session_distinct(self):
        a = canonical_request_key("FUGLE", "/quote", {"a": 1, "b": 2}, "A", "session1")
        b = canonical_request_key("FUGLE", "/quote", {"b": 2, "a": 1}, "A", "session1")
        c = canonical_request_key("FUGLE", "/quote", {"b": 2, "a": 1}, "A", "session2")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_concurrent_consumers_only_one_can_call(self):
        store = SharedMockStore()
        results = []
        barrier = threading.Barrier(2)
        def task(i):
            barrier.wait()
            results.append(reserve(store, key(), "run" + str(i), "attempt1"))
        a = threading.Thread(target=task, args=(1,))
        b = threading.Thread(target=task, args=(2,))
        a.start(); b.start(); a.join(); b.join()
        self.assertEqual(sorted(results), ["BLOCK_IN_FLIGHT", "CALL_ONCE"])

    def test_success_result_reused_after_owner_cas(self):
        store = SharedMockStore()
        self.assertEqual(reserve(store, key(), "run1", "a1"), "CALL_ONCE")
        digest = hashlib.sha256(b"sample").hexdigest()
        self.assertFalse(finalize_ready(store, key(), "run1", "a1", "gs://test/result", digest))
        self.assertEqual(reserve(store, key(), "run2", "a1"), "BLOCK_IN_FLIGHT")
        store.write_result("gs://test/result", b"tampered")
        self.assertFalse(finalize_ready(store, key(), "run1", "a1", "gs://test/result", digest))
        store.write_result("gs://test/result", b"sample")
        self.assertFalse(finalize_ready(store, key(), "run2", "a1", "gs://test/result", digest))
        self.assertTrue(finalize_ready(store, key(), "run1", "a1", "gs://test/result", digest))
        self.assertEqual(reserve(store, key(), "run2", "a1"), "REUSE_READY")

    def test_missing_durable_verifier_must_not_promote_ready(self):
        store = SharedMockStore()
        reserve(store, key(), "run1", "a1")
        store.verify_durable_result = None
        digest = hashlib.sha256(b"sample").hexdigest()
        self.assertFalse(finalize_ready(store, key(), "run1", "a1", "gs://test/result", digest))
        self.assertEqual(reserve(store, key(), "run2", "a2"), "BLOCK_IN_FLIGHT")

    def test_durable_verify_failure_keeps_in_flight(self):
        store = SharedMockStore()
        reserve(store, key(), "run1", "a1")
        digest = hashlib.sha256(b"sample").hexdigest()
        store.write_result("gs://test/result", b"wrong")
        self.assertFalse(finalize_ready(store, key(), "run1", "a1", "gs://test/result", digest))
        self.assertEqual(reserve(store, key(), "run2", "a2"), "BLOCK_IN_FLIGHT")

    def test_timeout_uncertain_prevents_retry_and_other_owner(self):
        store = SharedMockStore()
        self.assertEqual(reserve(store, key(), "run1", "a1"), "CALL_ONCE")
        self.assertTrue(quarantine_uncertain(store, key(), "run1", "a1"))
        self.assertEqual(reserve(store, key(), "run1", "a2"), "BLOCK_RECONCILIATION_REQUIRED")
        self.assertEqual(reserve(store, key(), "run2", "a1"), "BLOCK_RECONCILIATION_REQUIRED")

    def test_cas_race_and_same_owner_replay_blocked(self):
        store = SharedMockStore()
        reserve(store, key(), "run1", "a1")
        record, version = store.read(key())
        self.assertFalse(store.compare_and_swap(key(), "stale-version", record))
        self.assertEqual(reserve(store, key(), "run1", "a1"), "BLOCK_IN_FLIGHT")
        self.assertFalse(finalize_ready(store, key(), "run1", "a2", "gs://test/out", "a" * 64))

    def test_invalid_digest_and_unverified_quota_cannot_be_ready(self):
        from research.sky_paid_api_dedup_contract import Record
        from datetime import datetime, timezone
        k = key()
        now = datetime.now(timezone.utc).isoformat()
        kwargs = dict(key=k, state="READY", owner_run_id="run1",
                      attempt_id="a1", created_at=now, updated_at=now,
                      result_uri="gs://object", result_sha256="z" * 64)
        with self.assertRaisesRegex(ValueError, "INVALID_RESULT_SHA256"):
            Record(**kwargs)
        kwargs["result_sha256"] = "a" * 64
        kwargs["quota_units"] = -1
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_QUOTA_UNITS"):
            Record(**kwargs)
        store = SharedMockStore()
        reserve(store, k, "run1", "a1")
        self.assertFalse(finalize_ready(store,k,"run1","a1","gs://object","z"*64))
        self.assertEqual(reserve(store,k,"run2","a2"),"BLOCK_IN_FLIGHT")

    def test_no_stale_lease_takeover_and_invalid_time(self):
        from datetime import datetime
        store = SharedMockStore()
        self.assertRaises(ValueError, reserve, store, key(), "run1", "a1", datetime(2026, 11, 11))
        reserve(store, key(), "run1", "a1")
        self.assertEqual(reserve(store, key(), "run9", "a9"), "BLOCK_IN_FLIGHT")


if __name__ == "__main__":
    unittest.main()
