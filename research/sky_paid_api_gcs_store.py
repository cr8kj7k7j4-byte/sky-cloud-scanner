"""Research-only GCS generation-precondition backend for paid API dedup (#515).

No paid provider calls, no order execution, no automatic promotion.
The caller must supply authenticated GCS bucket access; missing permissions fail closed.
This backend is not wired into Production workflows.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re

from google.api_core.exceptions import NotFound, PreconditionFailed

from research.sky_paid_api_dedup_contract import Record

_KEY = re.compile(r"^[0-9a-f]{64}$")
_PREFIX = "sky/research/paid-api-dedup/v1"
_MAX_RESULT_BYTES = 8 * 1024 * 1024


class GcsAtomicStore:
    """Independent Runner-safe CAS: GCS generation preconditions, no local lock."""

    def __init__(self, bucket, prefix: str = _PREFIX):
        if (not prefix.startswith("sky/research/paid-api-dedup/")
                or ".." in prefix or "//" in prefix or prefix.endswith("/")):
            raise ValueError("UNSAFE_RESEARCH_PREFIX")
        if not getattr(bucket, "name", None):
            raise ValueError("GCS_BUCKET_REQUIRED")
        self.bucket = bucket
        self.prefix = prefix

    def _object(self, kind: str, key: str) -> str:
        if not isinstance(key, str) or not _KEY.fullmatch(key):
            raise ValueError("INVALID_REQUEST_KEY")
        return f"{self.prefix}/{kind}/{key}.json"

    @staticmethod
    def _payload(record: Record) -> bytes:
        return (json.dumps(asdict(record), sort_keys=True, separators=(",", ":"))
                + "\n").encode("utf-8")

    def create_if_absent(self, key: str, record: Record) -> bool:
        if record.key != key:
            raise ValueError("RECORD_KEY_MISMATCH")
        blob = self.bucket.blob(self._object("records", key))
        try:
            blob.upload_from_string(
                self._payload(record), content_type="application/json",
                if_generation_match=0,
            )
            return True
        except PreconditionFailed:
            return False

    def read(self, key: str) -> tuple[Record, str] | None:
        blob = self.bucket.blob(self._object("records", key))
        try:
            blob.reload()
            generation = int(blob.generation)
            payload = blob.download_as_bytes(if_generation_match=generation)
        except NotFound:
            return None
        # A concurrent rewrite is not a clean miss: surface error and fail closed.
        record = Record(**json.loads(payload))
        if record.key != key:
            raise ValueError("REMOTE_RECORD_KEY_MISMATCH")
        return record, str(generation)

    def compare_and_swap(self, key: str, version: str, record: Record) -> bool:
        if record.key != key or not str(version).isdecimal() or int(version) <= 0:
            raise ValueError("INVALID_CAS_REQUEST")
        blob = self.bucket.blob(self._object("records", key))
        try:
            blob.upload_from_string(
                self._payload(record), content_type="application/json",
                if_generation_match=int(version),
            )
            return True
        except PreconditionFailed:
            return False

    def persist_research_result_if_absent(self, key: str, payload: bytes):
        """Write immutable synthetic bytes, never a Fugle response."""
        if not isinstance(payload, bytes) or not 0 < len(payload) <= 4096:
            raise ValueError("RESEARCH_RESULT_SIZE_INVALID")
        blob = self.bucket.blob(self._object("results", key))
        try:
            blob.upload_from_string(
                payload, content_type="application/json", if_generation_match=0,
            )
        except PreconditionFailed:
            raise ValueError("RESEARCH_RESULT_ALREADY_EXISTS")
        uri = f"gs://{self.bucket.name}/{self._object('results', key)}"
        digest = hashlib.sha256(payload).hexdigest()
        if self.verify_durable_result(uri, digest) is not True:
            raise ValueError("RESEARCH_RESULT_NOT_DURABLE")
        return uri, digest

    def verify_durable_result(self, uri: str, digest: str) -> bool:
        if not isinstance(digest, str) or not _KEY.fullmatch(digest):
            return False
        base = f"gs://{self.bucket.name}/{self.prefix}/results/"
        if not isinstance(uri, str) or not uri.startswith(base):
            return False
        object_name = uri[len(f"gs://{self.bucket.name}/"):]
        key_part = object_name[len(f"{self.prefix}/results/"):]
        if not key_part.endswith(".json") or not _KEY.fullmatch(key_part[:-5]):
            return False
        blob = self.bucket.blob(object_name)
        try:
            blob.reload()
            if blob.size is None or blob.size > _MAX_RESULT_BYTES:
                return False
            data = blob.download_as_bytes(if_generation_match=int(blob.generation))
        except (NotFound, PreconditionFailed):
            return False
        return hashlib.sha256(data).hexdigest() == digest
