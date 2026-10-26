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

data=m._request_chunk("2330",date(2026,10,1),date(2026,10,1),timeframe="1",request_get=fake_get,sleep_fn=lambda x:None)
assert len(data)==1
assert seen["timeframe"]=="1"

with tempfile.TemporaryDirectory() as td:
    item={"symbol":"2330","exchange":"TWSE"}
    r=m.download_symbol(item,date(2026,10,1),date(2026,10,1),Path(td),timeframe="1",request_get=fake_get,sleep_fn=lambda x:None)
    files=list(Path(td).rglob("*_1m.json"))
    assert r["bars"]==1
    assert len(files)==1
    obj=json.loads(files[0].read_text(encoding="utf-8"))
    assert obj["timeframe"]=="1"

print("PASS timeframe parameterization")
