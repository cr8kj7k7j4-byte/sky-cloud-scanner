from __future__ import annotations
import importlib.util

spec=importlib.util.spec_from_file_location("dl","research/download_false_reclaim_short_1m.py")
dl=importlib.util.module_from_spec(spec);spec.loader.exec_module(dl)
assert dl.fourth_tick_below(10.00)==9.96
assert dl.fourth_tick_below(50.00)==49.80
assert dl.fourth_tick_below(100.00)==99.60

bars=[]
for i in range(80):
    hh=f"09:{i:02d}" if i<60 else f"10:{i-60:02d}"
    px=10.0
    bars.append({"date":f"2026-10-01T{hh}:00+08:00","open":px,"high":px,"low":px,"close":px,"volume":100})
c=dl.compact_chunk(bars)
assert len(c)==1
assert "09:01" in c[0]["short_outcomes"]
print("PASS False-Reclaim Short downloader")
