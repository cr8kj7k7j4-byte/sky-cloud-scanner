
import sys
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.backtest_trigger_event import (
    group_day, prev_close_map, detect_vwap_reclaim, detect_platform_breakout,
    validate_trade, simulate, metrics
)

def bar(ts,o,h,l,c,v,avg):
    return {"date":ts.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v,"average":avg}

def main():
    dt=datetime.fromisoformat("2026-01-02T09:05:00+08:00")
    bars=[
        bar(dt,10,10.05,9.95,10,100,10),
        bar(dt+timedelta(minutes=5),10,10.02,9.92,9.98,100,10.00),
        bar(dt+timedelta(minutes=10),9.98,10.15,9.97,10.12,180,10.01),
        bar(dt+timedelta(minutes=15),10.12,10.35,10.08,10.30,180,10.04),
    ]
    for b in bars: b["_dt"]=datetime.fromisoformat(b["date"])
    assert validate_trade(None) is None
    s=detect_vwap_reclaim(bars,2,9.8)
    assert s and s["setup"]=="VWAP_RECLAIM"
    v=validate_trade(s); assert v is not None
    sim=simulate(bars,2,v,1.5); assert "net_r" in sim

    # platform breakout synthetic
    p=[]
    for i in range(4):
        p.append({"_dt":dt+timedelta(minutes=5*i),"open":10,"high":10.05,"low":9.95,
                  "close":10.00,"volume":100,"average":9.99})
    p.append({"_dt":dt+timedelta(minutes=20),"open":10.01,"high":10.25,"low":10,
              "close":10.20,"volume":200,"average":10.01})
    ps=detect_platform_breakout(p,4,9.8)
    assert ps and ps["setup"]=="PLATFORM_BREAKOUT"

    rows=[{"net_r":1.0,"mfe_r":1.5,"mae_r":-.3},{"net_r":-1.0,"mfe_r":.2,"mae_r":-1.0}]
    m=metrics(rows); assert m["n"]==2 and m["pf"]==1.0
    assert metrics([])["n"]==0
    print("PASS 7/7 trigger-event unit tests")

if __name__=="__main__": main()
