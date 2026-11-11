"""Offline two-client Redis NX/WATCH CAS contract; no live network or provider."""
import hashlib
import threading
import unittest

from redis.exceptions import WatchError

from research.sky_paid_api_dedup_contract import (
    canonical_request_key, finalize_ready, reserve,
)
from research.sky_paid_api_redis_store import RedisAtomicStore


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.versions = {}
        self.lock = threading.Lock()

    def set(self, key, value, nx=False):
        with self.lock:
            if nx and key in self.data:
                return False
            self.data[key] = bytes(value)
            self.versions[key] = self.versions.get(key, 0) + 1
            return True

    def get(self, key):
        with self.lock:
            return self.data.get(key)

    def pipeline(self, transaction=True):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.watched = {}
        self.pending = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.watched.clear()
        self.pending.clear()

    def watch(self, key):
        with self.client.lock:
            self.watched[key] = self.client.versions.get(key, 0)

    def get(self, key):
        return self.client.get(key)

    def multi(self):
        return None

    def set(self, key, value):
        self.pending.append((key, bytes(value)))

    def execute(self):
        with self.client.lock:
            if any(self.client.versions.get(k, 0) != version
                   for k, version in self.watched.items()):
                raise WatchError("simulated concurrent modification")
            for key, value in self.pending:
                self.client.data[key] = value
                self.client.versions[key] = self.client.versions.get(key, 0) + 1


def sample_key():
    return canonical_request_key(
        "SYNTHETIC_NO_FUGLE", "/none",
        {"id": "offline"}, "RESEARCH_ONLY", "test-run",
    )


class RedisCasTests(unittest.TestCase):
    def test_two_clients_one_nx_owner(self):
        shared = FakeRedis()
        clients = [RedisAtomicStore(shared), RedisAtomicStore(shared)]
        barrier = threading.Barrier(2)
        decisions = []
        lock = threading.Lock()

        def task(index):
            barrier.wait()
            value = reserve(clients[index], sample_key(), f"run-{index}", "a1")
            with lock:
                decisions.append(value)

        runners = [threading.Thread(target=task, args=(i,)) for i in range(2)]
        for t in runners:
            t.start()
        for t in runners:
            t.join()
        self.assertEqual(sorted(decisions), ["BLOCK_IN_FLIGHT", "CALL_ONCE"])

    def test_ready_reuse_requires_persisted_bytes(self):
        shared = FakeRedis()
        owner = RedisAtomicStore(shared)
        consumer = RedisAtomicStore(shared)
        key = sample_key()
        self.assertEqual(reserve(owner, key, "owner", "a1"), "CALL_ONCE")
        self.assertEqual(reserve(consumer, key, "consumer", "a1"), "BLOCK_IN_FLIGHT")
        payload = b'{"synthetic":true,"provider_calls":0}'
        uri, digest = owner.persist_research_result_if_absent(key, payload)
        self.assertFalse(finalize_ready(consumer, key, "consumer", "a1", uri, digest))
        self.assertTrue(finalize_ready(owner, key, "owner", "a1", uri, digest))
        self.assertEqual(reserve(consumer, key, "consumer", "a2"), "REUSE_READY")
        shared.set(owner._key("results", key), b"tampered", nx=False)
        self.assertEqual(reserve(consumer, key, "consumer", "a3"),
                         "BLOCK_READY_RESULT_NOT_VERIFIED")

    def test_wrong_version_rejected_without_replacement(self):
        shared = FakeRedis()
        owner = RedisAtomicStore(shared)
        key = sample_key()
        reserve(owner, key, "owner", "a1")
        record, version = owner.read(key)
        self.assertFalse(owner.compare_and_swap(key, "999999", record))
        self.assertEqual(owner.read(key)[1], version)

    def test_unsafe_uri_and_key_blocked(self):
        store = RedisAtomicStore(FakeRedis())
        self.assertFalse(store.verify_durable_result(
            "redis://user:secret@host:6379/0", "a" * 64))
        with self.assertRaisesRegex(ValueError, "INVALID_REQUEST_KEY"):
            store.read("../other")


if __name__ == "__main__":
    unittest.main()
