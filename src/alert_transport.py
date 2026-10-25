from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

class AlertDeliveryError(RuntimeError):
    pass

def alert_fingerprint(channel: str, symbol: str, state: str, payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    raw = f"{channel}|{symbol}|{state}|{canonical}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def structured_event(event: str, **fields):
    return {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }

def deliver_with_retry(
    send: Callable[[], Any],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.25,
    sleep: Callable[[float], None] = time.sleep,
):
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    last_error: Optional[Exception] = None
    events = []
    for attempt in range(1, max_attempts + 1):
        try:
            result = send()
            events.append(structured_event("alert_delivery_success", attempt=attempt))
            return {"ok": True, "attempts": attempt, "result": result, "events": events}
        except Exception as exc:
            last_error = exc
            events.append(structured_event(
                "alert_delivery_failure",
                attempt=attempt,
                error_class=type(exc).__name__,
                error=str(exc),
            ))
            if attempt < max_attempts:
                sleep(base_delay_seconds * (2 ** (attempt - 1)))
    raise AlertDeliveryError(
        f"alert delivery failed after {max_attempts} attempts: {type(last_error).__name__}"
    ) from last_error

class DedupWindow:
    def __init__(self):
        self._seen: Dict[str, float] = {}

    def should_send(self, fingerprint: str, *, now_epoch: float, ttl_seconds: float) -> bool:
        expired = [k for k, ts in self._seen.items() if now_epoch - ts >= ttl_seconds]
        for k in expired:
            self._seen.pop(k, None)
        if fingerprint in self._seen:
            return False
        self._seen[fingerprint] = now_epoch
        return True
