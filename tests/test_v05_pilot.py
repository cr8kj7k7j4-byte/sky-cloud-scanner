
import json, sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.backtest_v05 import group_by_day, prev_close_map, snapshot, future_excursions, metrics

def make_day(day, start=20.0, drift=.001, avg_mult=.995, n=48):
    dt=datetime.fromisoformat(day+"T09:05:00+08:00")
    out=[]; px=start
    for i in range(n):
        op=px
        px*=1+drift
        out.append({
            "date":(dt+timedelta(minutes=5*i)).isoformat(),
            "open":op, "high":px*1.002, "low":px*.998, "close":px,
            "volume":100 if i%8 else 250, "average":px*avg_mult,
        })
    return out

def main():
    bars=make_day("2026-09-21")+make_day("2026-09-22")
    g=group_by_day(bars)
    assert len(g)==2
    pc=prev_close_map(g)
    days=sorted(g)
    assert pc[days[0]] is None and pc[days[1]] is not None

    s=snapshot(g[days[1]], datetime.strptime("10:10","%H:%M").time(), pc[days[1]])
    assert s is not None
    assert s["above_avg"] is True
    assert s["anti_chase_pass"] is True

    ex=future_excursions(g[days[1]], s["index"], 6)
    assert ex and "mfe_pct" in ex and "mae_pct" in ex

    # force anti-chase
    bh=make_day("2026-09-23", drift=.01, avg_mult=.95)
    gh=group_by_day(bh); dh=sorted(gh)[0]
    sh=snapshot(gh[dh], datetime.strptime("10:10","%H:%M").time(), 18.0)
    assert sh["anti_chase_pass"] is False

    rows=[
        {"x":True,"future_ret_pct":1.0,"mfe_pct":1.5,"mae_pct":-.3},
        {"x":True,"future_ret_pct":-0.5,"mfe_pct":.2,"mae_pct":-.8},
    ]
    m=metrics(rows,"x",.2)
    assert m["n"]==2
    assert abs(m["expectancy_net_pct"]-0.05)<1e-9
    assert m["profit_factor_net"] is not None

    assert metrics([], "x", .2)["n"]==0
    print("PASS 8/8 pilot workflow unit tests")

if __name__=="__main__":
    main()
