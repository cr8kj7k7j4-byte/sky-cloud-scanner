import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time

import requests

from .config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    REDIS_URL,
    ALERT_MAX_ATTEMPTS,
    ALERT_RETRY_BASE_SECONDS,
    ALERT_COOLDOWN_SECONDS,
    ALERT_DELIVERY_LOG,
)


_LOCAL_DEDUP = {}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _message_hash(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _write_delivery_log(record):
    path = Path(ALERT_DELIVERY_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": _utc_now(),
        "module": "P0-A",
        "service": "telegram",
        **record,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _claim_dedup(message_hash, cooldown_seconds):
    if cooldown_seconds <= 0:
        return True, "disabled"

    key = f"sky:p0a:alert:dedup:{message_hash}"
    if REDIS_URL:
        try:
            import redis
            client = redis.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            claimed = bool(
                client.set(key, "1", nx=True, ex=max(1, int(cooldown_seconds)))
            )
            return claimed, "redis"
        except Exception as exc:
            _write_delivery_log({
                "event": "alert_dedup_backend_degraded",
                "severity": "WARNING",
                "error_type": type(exc).__name__,
                "message_hash": message_hash,
                "delivery_status": "DEDUP_FALLBACK_LOCAL",
            })

    now = time.monotonic()
    expires_at = _LOCAL_DEDUP.get(message_hash, 0.0)
    if expires_at > now:
        return False, "local"
    _LOCAL_DEDUP[message_hash] = now + cooldown_seconds
    return True, "local"


def send_telegram(text):
    message = str(text)[:4000]
    message_hash = _message_hash(message)

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(message)
        _write_delivery_log({
            "event": "alert_delivery_skipped",
            "severity": "WARNING",
            "error_type": "MissingTelegramConfig",
            "message_hash": message_hash,
            "delivery_status": "SKIPPED_CONFIG",
            "attempts": 0,
            "escalation_required": True,
        })
        return False

    claimed, dedup_backend = _claim_dedup(
        message_hash, ALERT_COOLDOWN_SECONDS
    )
    if not claimed:
        _write_delivery_log({
            "event": "alert_delivery_deduplicated",
            "severity": "INFO",
            "error_type": None,
            "message_hash": message_hash,
            "delivery_status": "DEDUPLICATED",
            "dedup_backend": dedup_backend,
            "attempts": 0,
            "escalation_required": False,
        })
        return True

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    last_error = None
    max_attempts = max(1, int(ALERT_MAX_ATTEMPTS))

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            response.raise_for_status()
            _write_delivery_log({
                "event": "alert_delivery",
                "severity": "INFO",
                "error_type": None,
                "message_hash": message_hash,
                "delivery_status": "DELIVERED",
                "dedup_backend": dedup_backend,
                "attempts": attempt,
                "escalation_required": False,
            })
            return True
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                _write_delivery_log({
                    "event": "alert_delivery_retry",
                    "severity": "WARNING",
                    "error_type": type(exc).__name__,
                    "message_hash": message_hash,
                    "delivery_status": "RETRYING",
                    "attempts": attempt,
                    "escalation_required": False,
                })
                time.sleep(
                    max(0.0, float(ALERT_RETRY_BASE_SECONDS))
                    * (2 ** (attempt - 1))
                )

    _write_delivery_log({
        "event": "alert_delivery_failed",
        "severity": "ERROR",
        "error_type": type(last_error).__name__ if last_error else "UnknownError",
        "message_hash": message_hash,
        "delivery_status": "FAILED",
        "attempts": max_attempts,
        "escalation_required": True,
    })
    print(
        "P0-A alert delivery failed after retries; "
        f"message_hash={message_hash[:12]}"
    )
    return False
