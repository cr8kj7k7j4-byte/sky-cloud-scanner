"""Offline generation-precondition tests. NO cloud network or Fugle calls."""
import hashlib
import json
import threading
import unittest

from google.api_core.exceptions import NotFound, PreconditionFailed

from research.sky_paid_api_dedup_contract import (
    canonical_request_key, finalize_ready, reserve,
)
from research.sky_paid_api_gcs_store import GcsAtomicStore


class FakeBucket:
    name = "research-test-bucket"

    def __init__(self):
        self.lock = threading.Lock()
        self.objects = {}
        self.next_generation = 100

    def blob(self, name):
        return FakeBlob(self, name)


class FakeBlob:
    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name
        self.generation = None
        self.size = None

    def upload_from_string(self, data, *, content_type, if_generation_match):
        raw = data.encode() if isinstance(data, str) else bytes(data)
        with self.bucket.lock:
            current = self.bucket.objects.get(self.name)
            if if_generation_match == 0:
                if current is not None:
                    raise PreconditionFailed("already exists")
            elif current is None or current[0] != if_generation_match:
                raise PreconditionFailed("CAS conflict")
            self.bucket.next_generation += 1
            generation = self.bucket.next_generation
            self.bucket.objects[self.name] = (generation, raw)
            self.generation, self.size = generation, len(raw)

    def reload(self):
        with self.bucket.lock:
            current = self.bucket.objects.get(self.name)
            if current is None:
                raise NotFound("not found")
            self.generation, self.size = current[0], len(current[1])

    def download_as_bytes(self, *, if_generation_match):
        with self.bucket.lock:
            current = self.bucket.objects.get(self.name)
            if current is None:
                raise NotFound("missing")
            if current[0] != if_generation_match:
                raise PreconditionFailed("generation changed")
            return current[1]


def key():
    return canonical_request_key(
        "RESEARCH_MOCK_PROVIDER", "/synthetic", {"run": "acceptance"},
        "NO_PAID_ENTITLEMENT", "test",
    )


class GcsCasStoreTests(unittest.TestCase):
    def test_two_independent_clients_share_one_atomic_reservation(self):
        bucket = FakeBucket()
        clients = [GcsAtomicStore(bucket), GcsAtomicStore(bucket)]
        gate = threading.Barrier(2)
        results = []
        lock = threading.Lock()

        def worker(i):
            gate.wait()
            result = reserve(clients[i], key(), f"run-{i}", "attempt-1")
            with lock:
                results.append(result)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), ["BLOCK_IN_FLIGHT", "CALL_ONCE"])

    def test_persisted_bytes_cas_and_tamper_detection(self):
        bucket = FakeBucket()
        owner = GcsAtomicStore(bucket)
        reader = GcsAtomicStore(bucket)
        k = key()
        self.assertEqual(reserve(owner, k, "owner", "one"), "CALL_ONCE")
        self.assertEqual(reserve(reader, k, "other", "one"), "BLOCK_IN_FLIGHT")
        raw = b'{"synthetic":true,"provider_requests":0}'
        uri, digest = owner.persist_research_result_if_absent(k, raw)
        self.assertFalse(finalize_ready(reader, k, "other", "one", uri, digest))
        self.assertTrue(finalize_ready(owner, k, "owner", "one", uri, digest))
        self.assertEqual(reserve(reader, k, "other", "two"), "REUSE_READY")
        data_path = owner._object("results", k)
        with bucket.lock:
            generation, _ = bucket.objects[data_path]
            bucket.objects[data_path] = (generation + 1, b"ALTERED")
        self.assertEqual(reserve(reader, k, "other", "three"),
                         "BLOCK_READY_RESULT_NOT_VERIFIED")

    def test_bad_bucket_uri_and_wrong_request_key_fail_closed(self):
        bucket = FakeBucket()
        store = GcsAtomicStore(bucket)
        k = key()
        self.assertFalse(store.verify_durable_result("gs://evil/results/file", "a" * 64))
        self.assertFalse(store.verify_durable_result(
            f"gs://{bucket.name}/sky/research/paid-api-dedup/v1/results/other.json",
            "a" * 64,
        ))
        with self.assertRaisesRegex(ValueError, "INVALID_REQUEST_KEY"):
            store.read("../escape")

    def test_missing_result_cannot_advance_ready(self):
        bucket = FakeBucket()
        store = GcsAtomicStore(bucket)
        k = key()
        reserve(store, k, "run1", "a1")
        uri = f"gs://{bucket.name}/{store._object('results', k)}"
        self.assertFalse(finalize_ready(store, k, "run1", "a1", uri, "a" * 64))
        self.assertEqual(reserve(store, k, "run2", "a2"), "BLOCK_IN_FLIGHT")


if __name__ == "__main__":
    unittest.main()
