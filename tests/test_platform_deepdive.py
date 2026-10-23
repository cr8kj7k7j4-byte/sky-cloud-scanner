
import sys
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.backtest_platform_deepdive import detect_platform, simulate, calc, bucket, time_bucket

def main():
    dt=datetime.fromisoformat("2026-01-02T09:05:00+08:00")
    bars=[]
    for i in range(4):
        bars.append({"_dt":dt+timedelta(minutes=5*i),"open":10,"high":10.05,"low":9.95,
                     "close":10.00,"volume":100,"average":9.99})
    bars.append({"_dt":dt+timedelta(minutes=20),"open":10.01,"high":10.25,"low":10,
                 "close":10.20,"volume":200,"average":10.01})
    s=detect_platform(bars,4,9.8)
    assert s is not None
    assert s["volume_ratio"]==2.0
    assert s["breakout_pct"]>0
    assert 0.3<=s["risk_pct"]<=2.5
    assert time_bucket("10:15")=="09:50-10:30"
    assert bucket(2.2,[1.5,2,3,5,999],["1.5-2x","2-3x","3-5x","5x+"])=="2-3x"
    rows=[{"gross_r":1.0,"risk_pct":1.0},{"gross_r":-1.0,"risk_pct":1.0}]
    m=calc(rows,.25)
    assert m["n"]==2 and m["expectancy_r"]<0
    print("PASS 7/7 platform deep-dive unit tests")

if __name__=="__main__": main()
