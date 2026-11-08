"""Create-only local research event ledger for Sky Meta-Filter V0.1.

Offline connector contract only. Callers must separately provision an approved
private durable storage destination. No automatic cloud access or scheduled jobs.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re

from research.sky_meta_filter_v0_1 import validate_observation


def canonical(row):
    return json.dumps(row, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":")).encode("utf-8")


def archive_once(record, *, root):
    """Fail closed; preserve ACCEPT, REJECT and pending identical under replay.

    A stored event is *not* evidence of live fills or independent provenance.
    """
    normalized = validate_observation(record)
    if not isinstance(root, (str, Path)) or not str(root):
        raise ValueError("private_ledger_root_required")
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("private_ledger_root_must_be_absolute")
    sid = record["signal_id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", sid):
        raise ValueError("unsafe_signal_id")
    data = canonical(record)
    digest = sha256(data).hexdigest()
    folder = root / normalized["decision_date"] / normalized["symbol"]
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / (sid + ".json")
    try:
        with dest.open("xb") as output:
            output.write(data)
        status = "CREATED"
    except FileExistsError:
        existing = dest.read_bytes()
        if existing != data:
            raise ValueError("immutable_signal_conflict")
        status = "ALREADY_EXISTS_IDENTICAL"
    return {"signal_id":sid, "status":status,
            "object_sha256":digest,"path":str(dest),
            "production_eligible":False,"actual_fill":False}
