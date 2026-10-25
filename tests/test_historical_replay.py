from datetime import datetime, timedelta

from src.historical_replay import (
    FORMAL_SCAN_TIMES,
    ReplayPolicy,
    build_symbol_snapshots,
    replay_universe,
)


def _bars():
    rows=[]
    start=datetime(2026,10,20,9,0)
    for day_offset in range(2):
        day=start+timedelta(days=day_offset)
        base=10.0+day_offset
        for i in range(20):
            dt=day+timedelta(minutes=5*i)
            close=base+0.02*i
            rows.append({
                "date":dt.isoformat(),
                "open":close-0.01,
                "high":close+0.05,
                "low":close-0.05,
                "close":close,
                "volume":100+i,
                "average":base+0.01*i,
            })
    return rows


def test_formal_scan_times_are_current_sky_schedule():
    assert [x.strftime("%H:%M") for x in FORMAL_SCAN_TIMES] == [
        "09:05","09:15","09:30","09:50","10:15"
    ]


def test_replay_uses_only_point_in_time_history():
    obj={"symbol":"2409","exchange":"TWSE","data":_bars()}
    rows=build_symbol_snapshots(
        obj,
        policy=ReplayPolicy(min_history_bars=2,horizon_bars=3),
        scan_times=[FORMAL_SCAN_TIMES[1]],
    )
    assert rows
    row=rows[0]
    assert row["replay"]["point_in_time_only"] is True
    assert row["outcome"]["status"]=="COMPLETE"
    assert row["features"]["momentum_1"] is not None


def test_replay_adds_cross_sectional_relative_strength():
    a={"symbol":"A","exchange":"TWSE","data":_bars()}
    b_bars=_bars()
    for x in b_bars:
        x["close"]*=1.01
        x["high"]*=1.01
        x["low"]*=1.01
        x["open"]*=1.01
        x["average"]*=1.01
    b={"symbol":"B","exchange":"TWSE","data":b_bars}
    result=replay_universe(
        [a,b],
        policy=ReplayPolicy(min_history_bars=2,horizon_bars=3),
        scan_times=[FORMAL_SCAN_TIMES[1]],
    )
    assert result["production_eligible"] is False
    assert result["count"] >= 2
    assert all("market_context" in x for x in result["rows"])
    assert all(x["features"].get("relative_strength") is not None for x in result["rows"])
