import json
import os
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_LOG_PATH = "output/system.jsonl"


def emit(
    event,
    *,
    module,
    service,
    request_id=None,
    symbol=None,
    strategy_version=None,
    severity="INFO",
    error_type=None,
    latency_ms=None,
    extra=None,
    path=None,
):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": module,
        "service": service,
        "symbol": symbol,
        "strategy_version": strategy_version,
        "request_id": request_id,
        "event": event,
        "severity": severity,
        "error_type": error_type,
        "latency_ms": latency_ms,
    }
    if extra:
        payload["extra"] = dict(extra)

    target = Path(path or os.getenv("SKY_STRUCTURED_LOG", DEFAULT_LOG_PATH))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:
        # Logging must never fabricate a successful scan or change trading logic.
        # Emit a minimal stderr/stdout fallback without secrets.
        print(
            json.dumps(
                {
                    "timestamp": payload["timestamp"],
                    "module": module,
                    "service": service,
                    "event": "structured_log_write_failed",
                    "severity": "ERROR",
                    "error_type": type(exc).__name__,
                    "request_id": request_id,
                },
                ensure_ascii=False,
            )
        )
    return payload
