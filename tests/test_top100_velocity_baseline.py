from datetime import datetime, timedelta, timezone

from research.backtest_top100_velocity_baseline import (
    extract_symbol_snapshots,
    metrics,
    adjudicate,
)

TZ = timezone(timedelta(hours=8))


def _bar(ts, o, h, l, c, v):
    return {
        "date": ts.isoformat(),
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "average": c,
    }


def test_extract_uses_only_completed_feature_bar_and_next_bar_entry():
    rows = []
    day1 = datetime(2026, 1, 5, 9, 0, tzinfo=TZ)
    for i in range(54):
        ts = day1 + timedelta(minutes=5*i)
        px = 50 + 0.01*i
        rows.append(_bar(ts, px, px+0.1, px-0.1, px+0.02, 10+i))
    day2 = datetime(2026, 1, 6, 9, 0, tzinfo=TZ)
    for i in range(54):
        ts = day2 + timedelta(minutes=5*i)
        px = 51 + 0.02*i
        rows.append(_bar(ts, px, px+0.1, px-0.1, px+0.03, 20+i))

    payload = {"symbol":"1111","exchange":"TWSE","data":rows}
    snaps = extract_symbol_snapshots(payload)
    s915 = [x for x in snaps if x[2]=="2026-01-06" and x[3]=="09:15"][0]

    # tuple: symbol,exchange,day,obs,price,...,entry,exit,mfe,mae,...
    feature_price = s915[4]
    entry = s915[7]
    assert round(feature_price, 6) == round(51 + 0.02*2 + 0.03, 6)  # 09:10 close
    assert round(entry, 6) == round(51 + 0.02*3, 6)  # 09:15 open


def test_metrics_and_adjudication_reject_negative_after_cost():
    trades = [
        {"session_date":"2026-01-01","obs":"09:15","net_return_045":-0.01,"mfe":0.01,"mae":-0.01},
        {"session_date":"2026-01-01","obs":"09:30","net_return_045":0.002,"mfe":0.01,"mae":-0.01},
    ]
    m = metrics(trades, "net_return_045")
    assert m["expectancy"] < 0
    assert adjudicate(m, {}, {}) == "HOLD_INSUFFICIENT_SAMPLE"


if __name__ == "__main__":
    test_extract_uses_only_completed_feature_bar_and_next_bar_entry()
    test_metrics_and_adjudication_reject_negative_after_cost()
    print("ok")
