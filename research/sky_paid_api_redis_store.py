"""Research-only Redis SET NX + WATCH/MULTI/EXEC CAS backend.

No provider calls, broker orders, or model promotion. The Redis server's
persistence / eviction policy MUST be audited before paid traffic integration.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re

from redis.exceptions import WatchError

from research.sky_paid_api_dedup_contract import Record

_HEX = re.compile(r"^[0-9a-f]{64}$")
_DEFAULT_PREFIX = "sky:research:paid-api-dedup:redis-cas-v1"


class RedisAtomicStore:
    def __init__(self, client, prefix: str = _DEFAULT_PREFIX):
        if (not prefix.startswith("sky:research:paid-api-dedup:")
                or any(c in prefix for c in ("\n", "\r", " ", "/", "*"))
                or len(prefix) > 150):
            raise ValueError("UNSAFE_RESEARCH_PREFIX")
        self.client = client
        self.prefix = prefix

    def _key(self, suffix: str, key: str) -> str:
        if not isinstance(key, str) or not _HEX.fullmatch(key):
            raise ValueError("INVALID_REQUEST_KEY")
        return f"{self.prefix}:{suffix}:{key}"

    @staticmethod
    def _pack(record: Record, revision: int) -> bytes:
        if revision < 1:
            raise ValueError("INVALID_REVISION")
        return (json.dumps({"revision": revision, "record": asdict(record)},
                           sort_keys=True, separators=(",", ":")) + "\n").encode()

    @staticmethod
    def _unpack(raw: bytes, key: str) -> tuple[Record, int]:
        if not isinstance(raw, bytes):
            raise ValueError("REMOTE_RECORD_NOT_BYTES")
        obj = json.loads(raw)
        revision = obj.get("revision")
        if type(revision) is not int or revision < 1:
            raise ValueError("INVALID_REMOTE_REVISION")
        record = Record(**obj["record"])
        if record.key != key:
            raise ValueError("REMOTE_RECORD_KEY_MISMATCH")
        return record, revision

    def create_if_absent(self, key: str, record: Record) -> bool:
        if key != record.key:
            raise ValueError("RECORD_KEY_MISMATCH")
        return self.client.set(
            self._key("records", key), self._pack(record, 1),
            nx=True,
        ) is True

    def read(self, key: str) -> tuple[Record, str] | None:
        raw = self.client.get(self._key("records", key))
        if raw is None:
            return None
        record, revision = self._unpack(raw, key)
        return record, str(revision)

    def compare_and_swap(self, key: str, version: str, record: Record) -> bool:
        if (key != record.key or not isinstance(version, str)
                or not version.isdecimal() or int(version) < 1):
            raise ValueError("INVALID_CAS_REQUEST")
        rk = self._key("records", key)
        with self.client.pipeline(transaction=True) as pipe:
            try:
                pipe.watch(rk)
                raw = pipe.get(rk)
                if raw is None:
                    return False
                _current, revision = self._unpack(raw, key)
                if revision != int(version):
                    return False
                pipe.multi()
                pipe.set(rk, self._pack(record, revision + 1))
                pipe.execute()
                return True
            except WatchError:
                return False

    def persist_research_result_if_absent(self, key: str, payload: bytes):
        if not isinstance(payload, bytes) or not 0 < len(payload) <= 4096:
            raise ValueError("SYNTHETIC_RESULT_SIZE_INVALID")
        if self.client.set(self._key("results", key), payload, nx=True) is not True:
            raise ValueError("SYNTHETIC_RESULT_ALREADY_EXISTS")
        uri = f"skyredis://{self.prefix}/results/{key}"
        digest = hashlib.sha256(payload).hexdigest()
        if self.verify_durable_result(uri, digest) is not True:
            raise ValueError("SYNTHETIC_RESULT_BYTES_UNVERIFIED")
        return uri, digest

    def verify_durable_result(self, uri: str, digest: str) -> bool:
        if not isinstance(digest, str) or not _HEX.fullmatch(digest):
            return False
        path = f"skyredis://{self.prefix}/results/"
        if not isinstance(uri, str) or not uri.startswith(path):
            return False
        key = uri[len(path):]
        if not _HEX.fullmatch(key):
            return False
        payload = self.client.get(self._key("results", key))
        if not isinstance(payload, bytes) or len(payload) > 8 * 1024 * 1024:
            return False
        return hashlib.sha256(payload).hexdigest() == digest
