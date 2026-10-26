from __future__ import annotations
import importlib.util, json, tempfile
from pathlib import Path

spec=importlib.util.spec_from_file_location("d","research/backtest_opening_retest_reclaim_baseline_d.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

with tempfile.TemporaryDirectory() as td:
    root=Path(td);(root/"TWSE").mkdir()
    day={"date":"2026-10-01","session_open":10.0,"session_close":10.5,
      "bars":{
        "09:00":{"open":10.0,"high":10.1,"low":10.0,"close":10.1,"volume":100},
        "09:01":{"open":10.1,"high":10.15,"low":9.98,"close":10.0,"volume":120},
        "09:02":{"open":10.0,"high":10.12,"low":10.0,"close":10.1,"volume":140}},
      "outcomes":{"09:03":{"entry":10.15,"entry_status":"ENTRY_4TICK_ZONE","stop_aware_exit_30m":10.4,"stop_aware_exit_60m":10.5,"session_close":10.5,"open_stop_triggered":False,"high_to_close":10.8,"low_to_close":10.05}}}
    payload={"symbol":"1101","exchange":"TWSE","schema_version":"OPENING_ACCELERATION_1M_COMPACT_V1_1_4TICK_STOP","days":[day]}
    (root/"TWSE"/"1101_opening_1m.json").write_text(json.dumps(payload),encoding="utf-8")
    trades,build=d.load_trades(str(root))
    assert len(trades)==1,trades
    t=trades[0]
    assert t["reclaim_bar"]=="09:02" and t["entry_obs"]=="09:03"
    assert abs(t["entry"]-10.15)<1e-12
    print("PASS Opening Retest Reclaim Baseline D")
