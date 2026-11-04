from __future__ import annotations
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("baseline_f",str(Path("research/backtest_baseline_f_cross_sectional_short.py")))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
assert abs(mod.true_short(0.10)-(0.10/1.10))<1e-12
assert abs(mod.true_short(-0.1)-(-0.1/0.9))<1e-12
assert mod.true_short(None) is None
import tempfile,json
from collections import defaultdict
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp)/"TWSE";p.mkdir()
 for i in range(102):
    symbol=str(1000+i)
    ret=-0.02 if i==0 else (-0.01 if i<51 else 0.01)
    obj={"schema_version":"FALSE_RECLAIM_SHORT_1M_COMPACT_V1_0","symbol":symbol,"exchange":"TWSE",
      "days":[{"date":"2026-05-01","session_open":10.0,"bars":{"09:05":{"close":10*(1+ret)}}}]}
    (p/f"{symbol}_false_reclaim_short_1m.json").write_text(json.dumps(obj))
 census,meta=mod.peer_census(temp)
 t={"symbol":"1000","exchange":"TWSE","session_date":"2026-05-01","breakdown_bar":"09:05","entry":9.9,"gross_60m":0.01,"half":"2026-H1"}
 selected,all_rows,exc=mod.contextualize([t],census)
 assert len(all_rows)==1
 assert len(selected)==1 and selected[0]["peer_count"]==101
 assert selected[0]["cross_sectional_residual"]<0
 assert mod.score(selected,"net_045")["n"]==1
 print("PASS Baseline F structural cross-section / true short return")
