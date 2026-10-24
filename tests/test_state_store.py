import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.monitor_engine import MonitorDecision
from src.state_store import MonitorStateStore, StateStoreError


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
        return True

    def ping(self):
        return True


def test_file_store_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    store = MonitorStateStore("file", file_path=path)
    d = MonitorDecision(symbol="2409", state="WATCH", action="觀察", reason="test")
    store.save([d])
    assert store.load() == {"2409": "WATCH"}
    assert store.health()["persistent"] is False


def test_redis_requires_url_or_client():
    try:
        MonitorStateStore("redis", redis_url="")
        assert False, "expected StateStoreError"
    except StateStoreError:
        pass


def test_redis_roundtrip_with_injected_client():
    fake = FakeRedis()
    store = MonitorStateStore("redis", redis_client=fake, redis_key="test:key")
    d = MonitorDecision(symbol="3543", state="NEAR_TRIGGER", action="等待", reason="test")
    store.save([d])
    assert store.load() == {"3543": "NEAR_TRIGGER"}
    health = store.health()
    assert health["persistent"] is True
    assert health["ok"] is True
