from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

HEALTH_CONTRACT_VERSION = "1.0"

def health_payload(*, service="sky-cloud-scanner", version=None):
    return {
        "status": "ok",
        "service": service,
        "version": version,
        "contract_version": HEALTH_CONTRACT_VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

def readiness_payload(*, source_health: Dict[str, Any] | None = None, state_health: Dict[str, Any] | None = None):
    source_health = source_health or {}
    state_health = state_health or {}
    failed_sources = [
        name for name, detail in source_health.items()
        if isinstance(detail, dict) and detail.get("ok") is False
    ]
    state_ok = state_health.get("ok", True) is not False
    ready = not failed_sources and state_ok
    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "failed_sources": failed_sources,
        "state_store_ok": state_ok,
        "contract_version": HEALTH_CONTRACT_VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "note": "Library contract only; no HTTP server or deployment role change is made here.",
    }
