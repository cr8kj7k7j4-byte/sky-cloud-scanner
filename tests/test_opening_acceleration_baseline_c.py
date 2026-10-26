from __future__ import annotations
import importlib.util
from datetime import datetime, timedelta, timezone

TAIPEI=timezone(timedelta(hours=8))

spec=importlib.util.spec_from_file_location("dl","research/download_opening_acceleration_1m.py")
dl=importlib.util.module_from_spec(spec); spec.loader.exec_module(dl)
spec2=importlib.util.spec_from_file_location("bt","research/backtest_opening_acceleration_baseline_c.py")
bt=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(bt)

def bar(hm,px,vol=100):
    return {
      "date":f"2026-10-01T{hm}:00+08:00",
      "open":px,"high":px*1.001,"low":px*0.999,"close":px,"volume":vol
    }

data=[]
base=datetime(2026,10,1,9,0,tzinfo=TAIPEI)
for i in range(80):
    t=(base+timedelta(minutes=i)).strftime("%H:%M")
    data.append(bar(t,10+i*0.01,100+i))
c=dl.compact_chunk(data)
assert len(c)==1
d=c[0]
assert "09:00" in d["bars"] and "09:14" in d["bars"] and "09:15" not in d["bars"]
assert "09:01" in d["outcomes"]
o=d["outcomes"]["09:01"]
assert o["entry"]>0 and o["exit_30m"]>0 and o["exit_60m"]>0
assert o["high_to_close"]>=o["entry"]

rows=[]
for i,s in enumerate(["1101","1102","1103","1104"]):
    rows.append({
      "symbol":s,"exchange":"TWSE","session_date":"2026-10-01","obs":"09:05",
      "gain_rank":10+i,"session_open":10.0,"price":10.2+i*0.01,
      "minutes_since_top100_entry":1,
      "rank_velocity_1m":5-i,"rank_velocity_3m":4-i,
      "ret_1m":0.01+i*0.001,"ret_3m":0.02+i*0.001,
      "volume_acceleration_1v3":0.5+i*0.1,
      "entry":10.2,"exit_30m":10.4,"exit_60m":10.5,"session_close":10.6,
      "high_30m":10.5,"low_30m":10.1,"high_60m":10.7,"low_60m":10.1,
      "high_to_close":10.8,"low_to_close":10.0,"prior_close":10.0,
      "split":"RESEARCH_TEST","half":"2026-H2"
    })
p=bt.select_variant(rows)
assert len(p)==3
assert all(x["net_60m_045"] is not None for x in p)
m=bt.metrics(p,"net_60m_045")
assert m["n"]==3
print("PASS Opening Acceleration unit tests")
