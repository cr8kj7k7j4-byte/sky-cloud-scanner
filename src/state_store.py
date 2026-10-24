import json
from pathlib import Path


class StateStoreError(RuntimeError):
    pass


class MonitorStateStore:
    """
    P0-A state persistence abstraction.

    backends:
    - file: local development only; container restarts may lose state.
    - redis: cloud persistence using REDIS_URL.

    Redis mode never silently falls back to file. A broken cloud state store
    must be visible rather than creating false continuity.
    """

    def __init__(self, backend="file", *, file_path="output/monitor_state.json",
                 redis_url="", redis_key="sky:p0a:monitor_state", redis_client=None):
        self.backend = str(backend or "file").strip().lower()
        self.file_path = Path(file_path)
        self.redis_url = str(redis_url or "").strip()
        self.redis_key = str(redis_key or "sky:p0a:monitor_state").strip()
        self._redis_client = redis_client

        if self.backend not in {"file", "redis"}:
            raise StateStoreError(f"不支援的 MONITOR_STATE_BACKEND: {self.backend}")
        if self.backend == "redis" and not self.redis_url and self._redis_client is None:
            raise StateStoreError("MONITOR_STATE_BACKEND=redis 但未設定 REDIS_URL")

    @property
    def persistent(self):
        return self.backend == "redis"

    def _redis(self):
        if self._redis_client is not None:
            return self._redis_client
        try:
            import redis
        except ImportError as e:
            raise StateStoreError("Redis backend 需要安裝 redis 套件") from e
        try:
            self._redis_client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            return self._redis_client
        except Exception as e:
            raise StateStoreError(f"Redis 初始化失敗: {type(e).__name__}") from e

    def load(self):
        if self.backend == "file":
            if not self.file_path.exists():
                return {}
            try:
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except Exception as e:
                raise StateStoreError(f"本機狀態讀取失敗: {type(e).__name__}") from e

        try:
            raw = self._redis().get(self.redis_key)
            if not raw:
                return {}
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except StateStoreError:
            raise
        except Exception as e:
            raise StateStoreError(f"Redis 狀態讀取失敗: {type(e).__name__}") from e

    def save(self, decisions):
        payload = {
            d.symbol: d.state
            for d in decisions
            if getattr(d, "symbol", None)
        }

        if self.backend == "file":
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.file_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                return payload
            except Exception as e:
                raise StateStoreError(f"本機狀態寫入失敗: {type(e).__name__}") from e

        try:
            self._redis().set(
                self.redis_key,
                json.dumps(payload, ensure_ascii=False),
            )
            return payload
        except Exception as e:
            raise StateStoreError(f"Redis 狀態寫入失敗: {type(e).__name__}") from e

    def health(self):
        if self.backend == "file":
            return {
                "backend": "file",
                "persistent": False,
                "ok": True,
                "warning": "本機檔案僅適合開發；容器重啟可能遺失狀態",
            }
        try:
            ok = bool(self._redis().ping())
            return {
                "backend": "redis",
                "persistent": True,
                "ok": ok,
                "key": self.redis_key,
            }
        except Exception as e:
            return {
                "backend": "redis",
                "persistent": True,
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
            }
