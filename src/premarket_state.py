from __future__ import annotations

import json


def load_premarket_event_snapshot(*, redis_url: str, redis_key: str):
    if not redis_url:
        return {
            "ok": False,
            "source": "none",
            "reason": "REDIS_URL_NOT_SET",
            "snapshot": None,
        }
    try:
        import redis
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=10,
        )
        raw = client.get(redis_key)
        if not raw:
            return {
                "ok": False,
                "source": "redis",
                "reason": "SNAPSHOT_NOT_FOUND",
                "snapshot": None,
            }
        data = json.loads(raw)
        return {
            "ok": True,
            "source": "redis",
            "reason": None,
            "snapshot": data,
        }
    except Exception as exc:
        return {
            "ok": False,
            "source": "redis",
            "reason": f"{type(exc).__name__}: {exc}",
            "snapshot": None,
        }
