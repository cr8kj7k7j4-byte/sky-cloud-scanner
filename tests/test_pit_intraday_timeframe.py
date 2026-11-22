from __future__ import annotations
import importlib.util
from datetime import date
from pathlib import Path
import tempfile
import json

spec=importlib.util.spec_from_file_location("dl","research/download_pit_universe_intraday.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Resp:
    status_code=200
    headers={}
    def raise_for_status(self): pass
    def json(self):
        return {"data":[{"date":"2026-10-01T09:00:00+08:00","open":10,"high":10.1,"low":9.9,"close":10.05,"volume":100}]}

seen={}
def fake_get(url,params,headers,timeout):
    seen.update(params)
    return Resp()

# No real provider requests or GitHub refs are created by these tests.
from unittest.mock import patch

paid_attempts = []
def no_network(*args, **kwargs):
    paid_attempts.append(1)
    raise AssertionError("UNGUARDED_PROVIDER_CALL")

# A missing paid atomic flag must not be bypassed by a mock transport.
with patch.dict("os.environ", {"SKY_PAID_ATOMIC_ENFORCE": ""}):
    try:
        m._request_chunk("2330",date(2026,10,1),date(2026,10,1),
                         timeframe="1",request_get=no_network)
        raise AssertionError("UNGUARDED_HISTORY_ACCEPTED")
    except RuntimeError as error:
        assert "HISTORICAL_PAID_GUARD_REQUIRED" in str(error)
assert paid_attempts == []

with patch.dict("os.environ", {"SKY_PAID_ATOMIC_ENFORCE": "1"}), patch.object(
        m, "guard_fugle_request",
        side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")):
    try:
        m._request_chunk("2330",date(2026,10,1),date(2026,10,1),
                         timeframe="1",request_get=no_network)
        raise AssertionError("DENIED_CLAIM_ACCEPTED")
    except RuntimeError as error:
        assert "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED" in str(error)
assert paid_attempts == []

claimed = []
def offline_guard(url, params):
    claimed.append((url, dict(params)))

with patch.dict("os.environ", {"SKY_PAID_ATOMIC_ENFORCE": "1"}), patch.object(
        m, "guard_fugle_request", side_effect=offline_guard):
    data=m._request_chunk("2330",date(2026,10,1),date(2026,10,1),timeframe="1",request_get=fake_get,sleep_fn=lambda x:None)
    assert len(data)==1
    assert seen["timeframe"]=="1"
    assert claimed[0][1]["timeframe"] == "1"

    with tempfile.TemporaryDirectory() as td:
        item={"symbol":"2330","exchange":"TWSE"}
        r=m.download_symbol(item,date(2026,10,1),date(2026,10,1),Path(td),timeframe="1",request_get=fake_get,sleep_fn=lambda x:None)
        files=list(Path(td).rglob("*_1m.json"))
        assert r["bars"]==1
        assert len(files)==1
        obj=json.loads(files[0].read_text(encoding="utf-8"))
        assert obj["timeframe"]=="1"

    class RateLimited:
        status_code = 429
        headers = {}
    calls = []
    def fake_429(*args, **kwargs):
        calls.append(1)
        return RateLimited()
    try:
        m._request_chunk("2330",date(2026,10,1),date(2026,10,1),
                         timeframe="1",request_get=fake_429, sleep_fn=lambda _:None)
        raise AssertionError("429_DID_NOT_BLOCK")
    except RuntimeError as error:
        assert "NO_RETRY" in str(error)
    assert len(calls) == 1

assert len(claimed) == 3
print("PASS PIT timeframe, atomic fail-closed, and no paid 429 retry")
