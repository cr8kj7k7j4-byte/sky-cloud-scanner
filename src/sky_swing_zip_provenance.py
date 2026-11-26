"""Verify actual GitHub Swing ZIP bytes before invoking the existing offline reader.

This pure offline adapter makes no network, quote or paid Fugle calls. Artifact
metadata MUST be retrieved independently from GitHub Actions for the expected
run. Its digest/identity must never be copied from the ZIP under test.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
import stat
from tempfile import TemporaryDirectory
from zipfile import ZipFile, BadZipFile

from .sky_swing_historical_reader import read_historical_observation

SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA256 = re.compile(r"sha256:[a-f0-9]{64}\Z")
MAX_ZIP = 20_000_000
MAX_UNPACKED = 35_000_000
MAX_FILES = 80


def _verified_zip(path: str | Path, metadata: dict, *, name: str, run_id: str) -> Path:
    if (not isinstance(metadata, dict) or
            metadata.get("name") != name or
            type(metadata.get("id")) is not int or metadata["id"] <= 0 or
            metadata.get("expired") is not False or
            not isinstance(metadata.get("digest"), str) or
            not SHA256.fullmatch(metadata["digest"])):
        raise ValueError("GITHUB_ARTIFACT_METADATA_INVALID")
    if not str(run_id).isdigit():
        raise ValueError("INVALID_RUN_ID")
    archive = Path(path)
    if not archive.is_file() or archive.is_symlink() or archive.stat().st_size > MAX_ZIP:
        raise ValueError("ARTIFACT_ZIP_MISSING_OR_OVERSIZE")
    computed = "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest()
    if computed != metadata["digest"]:
        raise ValueError("GITHUB_ARTIFACT_DIGEST_MISMATCH")
    return archive


def _extract_safe(archive: Path, destination: Path) -> None:
    with ZipFile(archive) as handle:
        files = handle.infolist()
        if len(files) > MAX_FILES or sum(f.file_size for f in files) > MAX_UNPACKED:
            raise ValueError("ARTIFACT_ZIP_RESOURCE_LIMIT")
        used = set()
        for item in files:
            name = item.filename
            parts = PurePosixPath(name)
            # Forbid traversal, hidden Unicode aliases, symlink / special files.
            if (not name or name.startswith("/") or "\\" in name or
                    any(part in ("", ".", "..") for part in name.split("/")) or
                    parts.is_absolute() or str(parts) in used):
                raise ValueError("ARTIFACT_UNSAFE_MEMBER")
            used.add(str(parts))
            file_type = (item.external_attr >> 16) & 0o170000
            if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("ARTIFACT_UNSAFE_MEMBER_TYPE")
            if item.is_dir():
                continue
            target = destination.joinpath(*parts.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError("ARTIFACT_PATH_ESCAPE")
            target.parent.mkdir(parents=True, exist_ok=True)
            with handle.open(item) as source, target.open("xb") as out:
                import shutil
                shutil.copyfileobj(source, out, 1024 * 1024)


def read_verified_swing_zips(
    source_zip: str | Path,
    source_metadata: dict,
    readback_zip: str | Path,
    readback_metadata: dict,
    *,
    expected_run_id: str,
    expected_head_sha: str,
    observed_at: datetime,
    expected_trade_date: str | None = None,
) -> dict:
    """Verify two independently downloaded same-run ZIPs, then read research.

    The caller independently obtains GitHub workflow run info, source/readback
    artifact metadata, ZIP bytes and exchange date. This function validates
    them and rejects 5D or fake Swing V1.0 receipts; it never authorizes trades.
    """
    hold = {
        "schema": "SKY_SWING_ZIP_PROVENANCE_V1",
        "status": "HOLD_EVIDENCE", "reason": "SOURCE_UNVERIFIED",
        "research_only": True, "new_entry_authorized": False,
        "production_eligible": False, "text": None,
    }
    if not SHA40.fullmatch(str(expected_head_sha)) or not str(expected_run_id).isdigit():
        return {**hold, "reason": "INVALID_EXPECTED_RUN_ID_OR_SHA"}
    if observed_at.tzinfo is None:
        return {**hold, "reason": "UNZONED_OBSERVATION_TIME"}
    try:
        source = _verified_zip(source_zip, source_metadata,
                               name=f"sky-swing-live-{expected_run_id}",
                               run_id=expected_run_id)
        readback = _verified_zip(readback_zip, readback_metadata,
                                 name=f"sky-swing-readback-{expected_run_id}",
                                 run_id=expected_run_id)
        if source_metadata["id"] == readback_metadata["id"]:
            raise ValueError("SOURCE_AND_READBACK_MUST_BE_DISTINCT")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source"
            receipt_root = root / "receipt"
            src.mkdir()
            receipt_root.mkdir()
            _extract_safe(source, src)
            _extract_safe(readback, receipt_root)
            receipt = receipt_root / "receipt.json"
            if not receipt.is_file():
                raise ValueError("READBACK_RECEIPT_MISSING")
            result = read_historical_observation(
                src, receipt,
                expected_run_id=expected_run_id,
                expected_head_sha=expected_head_sha,
                observed_at=observed_at,
                expected_trade_date=expected_trade_date,
            )
            if result["status"] != "PASS_HISTORICAL_RESEARCH_OBSERVATION_ONLY":
                return {**hold, "reason": result.get("reason", "READER_REJECTED")}
            # The receipt's main artifact ID must match independently obtained metadata.
            rb = json.loads(receipt.read_text(encoding="utf-8"))
            if rb.get("artifact_id") != source_metadata["id"]:
                raise ValueError("RECEIPT_ARTIFACT_ID_MISMATCH")
            return {
                **result,
                "schema": "SKY_SWING_ZIP_PROVENANCE_V1",
                "status": "PASS_ZIP_BYTES_AND_RESEARCH_OBSERVATION_ONLY",
                "source_artifact_id": source_metadata["id"],
                "source_zip_digest": source_metadata["digest"],
                "readback_artifact_id": readback_metadata["id"],
                "readback_zip_digest": readback_metadata["digest"],
                "github_run_metadata_certified": False,
                "exchange_calendar_certified": False,
                "new_entry_authorized": False,
                "production_eligible": False,
            }
    except (OSError, ValueError, KeyError, TypeError, BadZipFile, json.JSONDecodeError) as exc:
        return {**hold, "reason": str(exc)[:160]}
