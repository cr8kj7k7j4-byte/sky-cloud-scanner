"""Research-only cross-workflow paid-request contract.

A *shared* remote store implementing atomic create and compare-and-swap is required.
Per-run files, GitHub concurrency groups, and in-process locks DO NOT provide
cross-workflow exclusion. This module makes no provider calls and is not wired
into Production. Uncertain outcomes are fail-closed (never automatically retry).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Protocol, Any

STATES = {"IN_FLIGHT", "READY", "UNCERTAIN", "FAILED_BEFORE_SEND"}


def canonical_request_key(provider: str, endpoint: str, params: dict[str, Any],
                          entitlement: str, session: str) -> str:
    """Exclude secrets; include complete data identity, provider entitlement and session.

    Never include token, auth headers or user-identifying personal data in params.
    """
    if not all((provider, endpoint, entitlement, session)):
        raise ValueError("REQUEST_IDENTITY_INCOMPLETE")
    if not isinstance(params, dict):
        raise ValueError("INVALID_REQUEST_PARAMS")
    raw = json.dumps([provider, endpoint, entitlement, session, params],
                     sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Record:
    key: str
    state: str
    owner_run_id: str
    attempt_id: str
    created_at: str
    updated_at: str
    result_uri: str | None = None
    result_sha256: str | None = None
    provider_request_id: str | None = None
    quota_units: int | None = None
    usage_source: str | None = None

    def __post_init__(self):
        if (not isinstance(self.key, str) or len(self.key) != 64
                or any(c not in "0123456789abcdef" for c in self.key)
                or self.state not in STATES):
            raise ValueError("INVALID_RECORD")
        if not self.owner_run_id or not self.attempt_id:
            raise ValueError("MISSING_OWNER")
        if self.state == "READY" and not (self.result_uri and self.result_sha256):
            raise ValueError("READY_REQUIRES_VERIFIED_RESULT")
        if self.result_sha256 is not None and (
                not isinstance(self.result_sha256, str) or len(self.result_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.result_sha256)):
            raise ValueError("INVALID_RESULT_SHA256")
        if self.quota_units is not None and (type(self.quota_units) is not int or self.quota_units < 0):
            raise ValueError("UNVERIFIED_QUOTA_UNITS")


class AtomicStore(Protocol):
    """Implement with a real shared backend (e.g. GCS generation preconditions)."""
    def create_if_absent(self, key: str, record: Record) -> bool: ...
    def read(self, key: str) -> tuple[Record, str] | None: ...
    def compare_and_swap(self, key: str, version: str, record: Record) -> bool: ...


def reserve(store: AtomicStore, key: str, owner_run_id: str,
            attempt_id: str, now: datetime | None = None) -> str:
    """Return CALL_ONCE or REUSE_READY / BLOCK_*.

    A crashed/incomplete owner stays blocked until reconciled by operator.
    Never steal expired leases: unknown provider-send state could cause billing.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    stamp = now.astimezone(timezone.utc).isoformat()
    record = Record(key=key, state="IN_FLIGHT", owner_run_id=owner_run_id,
                    attempt_id=attempt_id, created_at=stamp, updated_at=stamp)
    if store.create_if_absent(key, record):
        return "CALL_ONCE"
    existing = store.read(key)
    if existing is None:
        return "BLOCK_INCONSISTENT_STORE"
    current, _ = existing
    if current.state == "READY":
        return "REUSE_READY"
    if current.state == "IN_FLIGHT":
        return "BLOCK_IN_FLIGHT"
    return "BLOCK_RECONCILIATION_REQUIRED"


def finalize_ready(store: AtomicStore, key: str, owner_run_id: str,
                   attempt_id: str, uri: str, digest: str,
                   provider_request_id: str | None = None,
                   quota_units: int | None = None,
                   usage_source: str | None = None) -> bool:
    """Owner-only CAS after *durable* result upload and content hash validation.

    The provider request ID may be unavailable; never invent it or a quota value.
    """
    from dataclasses import replace
    pair = store.read(key)
    if pair is None:
        return False
    record, version = pair
    if (record.state != "IN_FLIGHT" or record.owner_run_id != owner_run_id
            or record.attempt_id != attempt_id or not uri
            or not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)):
        return False
    updated = replace(record, state="READY", result_uri=uri,
                      result_sha256=digest, provider_request_id=provider_request_id,
                      quota_units=quota_units, usage_source=usage_source,
                      updated_at=datetime.now(timezone.utc).isoformat())
    return store.compare_and_swap(key, version, updated)


def quarantine_uncertain(store: AtomicStore, key: str, owner_run_id: str,
                         attempt_id: str) -> bool:
    """Record unknown provider outcome. No automatic reclaim or send retry."""
    from dataclasses import replace
    pair = store.read(key)
    if pair is None:
        return False
    record, version = pair
    if record.state != "IN_FLIGHT" or (record.owner_run_id, record.attempt_id) != (owner_run_id, attempt_id):
        return False
    return store.compare_and_swap(
        key, version, replace(record, state="UNCERTAIN",
                             updated_at=datetime.now(timezone.utc).isoformat()))
