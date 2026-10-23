
import sys
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.backtest_expanded import group_day,prev_close,snap,add_cross_section,flags,metrics

def mk(day,start=20,drift=.001,n=50):
    dt=datetime.fromisoformat(day+"T09:05:00+08:00"); out=[]; px=start
    for i in range(n):
        op=px; px*=1+drift
        out.append({"date":(dt+timedelta(minutes=5*i)).isoformat(),"open":op,
                    "high":px*1.002,"low":px*.998,"close":px,"volume":100,"average":px*.995})
    return out

def main():
    data=mk("2025-01-02")+mk("2025-01-03")
    by=group_day(data); assert len(by)==2
    pc=prev_close(by); ds=sorted(by); assert pc[ds[1]] is not None
    s=snap(by[ds[1]],datetime.strptime("10:10","%H:%M").time(),pc[ds[1]])
    assert s and s["above_avg"] and s["anti_pass"]
    rows=[
        {"date":"2025-01-03","scan_time":"10:10","change_pct":1.0,"above_avg":True,"anti_pass":True,
         "ret_12":1.0,"mfe_12":1.3,"mae_12":-.2},
        {"date":"2025-01-03","scan_time":"10:10","change_pct":-.5,"above_avg":False,"anti_pass":True,
         "ret_12":-.2,"mfe_12":.1,"mae_12":-.5},
        {"date":"2025-01-03","scan_time":"10:10","change_pct":2.0,"above_avg":True,"anti_pass":True,
         "ret_12":.5,"mfe_12":.8,"mae_12":-.3},
    ]
    add_cross_section(rows)
    assert all("market_rs_pass" in r for r in rows)
    assert flags(rows[0])["V04_BASE"] is True
    m=metrics(rows,"V04_BASE",12,.45); assert m["n"]==2
    assert "expectancy_net_pct" in m
    print("PASS 7/7 expanded backtest unit tests")

if __name__=="__main__": main()
