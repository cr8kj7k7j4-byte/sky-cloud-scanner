"""Offline integrity check for a downloaded, *same-run* Sky source inventory.

This validates artifact identity supplied by the independent downloader and
bytes listed in the inventory. It does NOT certify Fugle data or trading.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "SKY_W0_SAME_RUN_SOURCE_INVENTORY_V1"
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def verify_downloaded_inventory(
    extraction_root: str | Path,
    *,
    expected_run_id: str,
    expected_attempt: str,
    expected_head_sha: str,
    artifact_id: int,
) -> dict[str, Any]:
    """Fail closed unless downloaded contents bind to run, attempt and SHA.

    artifact_id MUST come from GitHub's run artifact metadata, not from the
    inventory itself. This function cannot prove remote download provenance.
    """
    if (not str(expected_run_id).isdigit()
            or not str(expected_attempt).isdigit()
            or not isinstance(expected_head_sha, str)
            or _SHA.fullmatch(expected_head_sha) is None
            or type(artifact_id) is not int or artifact_id <= 0):
        raise ValueError("INVALID_EXPECTED_PROVENANCE")
    root = Path(extraction_root).resolve(strict=True)
    manifest = root / "output/sky_quickscan_information/same_run_source_inventory.json"
    if (not manifest.is_file() or manifest.is_symlink()
            or not manifest.resolve().is_relative_to(root)):
        raise ValueError("INVENTORY_MISSING_OR_UNSAFE_PATH")
    inventory = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(inventory, dict) or inventory.get("schema") != SCHEMA:
        raise ValueError("INVALID_INVENTORY_SCHEMA")
    for field, expected in (
        ("run_id", expected_run_id),
        ("run_attempt", expected_attempt),
        ("head_sha", expected_head_sha),
    ):
        if inventory.get(field) != expected:
            raise ValueError(f"{field.upper()}_MISMATCH")
    if (inventory.get("production_eligible") is not False
            or inventory.get("trade_action") != "禁止交易"):
        raise ValueError("RESEARCH_SAFETY_GUARD_FAILED")
    sources = inventory.get("source_inventory")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("SOURCE_INVENTORY_EMPTY")
    checked = 0
    missing = []
    for name, entry in sources.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("INVALID_SOURCE_ENTRY")
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise ValueError("UNSAFE_SOURCE_PATH")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("UNSAFE_SOURCE_PATH")
        candidate = root / path
        if candidate.is_symlink() or not candidate.resolve().is_relative_to(root):
            raise ValueError("UNSAFE_SOURCE_PATH")
        if entry.get("raw_provider_source_certified") is not False:
            raise ValueError("UNVERIFIED_SOURCE_CERTIFICATION")
        digest = entry.get("sha256")
        if digest is None:
            if candidate.exists() or entry.get("status") != "HOLD_SOURCE_NOT_CAPTURED":
                raise ValueError("SOURCE_MISSING_STATUS_MISMATCH")
            missing.append(name)
            continue
        if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
            raise ValueError("INVALID_SOURCE_DIGEST")
        if not candidate.is_file() or candidate.is_symlink():
            raise ValueError("SOURCE_FILE_MISSING")
        raw = candidate.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("SOURCE_DIGEST_MISMATCH")
        if entry.get("byte_count") != len(raw):
            raise ValueError("SOURCE_SIZE_MISMATCH")
        checked += 1
    # A manifest with only missing sources has validated zero file bytes.
    # Never label that as a successful same-run integrity readback.
    if checked == 0:
        raise ValueError("NO_SOURCE_BYTES_VERIFIED")
    return {
        "status": "SAME_RUN_BYTES_VERIFIED_RESEARCH_ONLY",
        "run_id": expected_run_id,
        "run_attempt": expected_attempt,
        "head_sha": expected_head_sha,
        "artifact_id": artifact_id,
        "verified_file_count": checked,
        "missing_sources": missing,
        "production_eligible": False,
        "trade_action": "禁止交易",
        "provider_data_certified": False,
    }
