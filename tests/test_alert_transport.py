import pytest
from src.alert_transport import alert_fingerprint, deliver_with_retry, DedupWindow, AlertDeliveryError

def test_fingerprint_is_stable():
    a = alert_fingerprint("telegram","2409","TRIGGERED",{"b":2,"a":1})
    b = alert_fingerprint("telegram","2409","TRIGGERED",{"a":1,"b":2})
    assert a == b

def test_retry_then_success():
    calls = {"n":0}
    def send():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("temporary")
        return True
    r = deliver_with_retry(send, max_attempts=3, base_delay_seconds=0, sleep=lambda _: None)
    assert r["ok"] is True
    assert r["attempts"] == 3

def test_retry_exhausted():
    with pytest.raises(AlertDeliveryError):
        deliver_with_retry(lambda: (_ for _ in ()).throw(TimeoutError()), max_attempts=2, base_delay_seconds=0, sleep=lambda _: None)

def test_dedup_ttl():
    d = DedupWindow()
    assert d.should_send("x", now_epoch=100, ttl_seconds=60) is True
    assert d.should_send("x", now_epoch=120, ttl_seconds=60) is False
    assert d.should_send("x", now_epoch=161, ttl_seconds=60) is True
