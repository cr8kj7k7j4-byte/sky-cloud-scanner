from datetime import datetime, timedelta, timezone
import pytest
from research.three_model_research_signals import generate

TZ = timezone(timedelta(hours=8))
def bars(n=35, minutes=True):
    start = datetime(2026, 11, 5, 9, 0, tzinfo=TZ)
    delta = timedelta(minutes=5) if minutes else timedelta(days=1)
    return [dict(timestamp=(start+i*delta).isoformat(), open=50+i*.2,
        high=50+i*.2+.2, low=50+i*.2-.2, close=50+i*.2, volume=2000+i*20)
        for i in range(n)]
def payload():
    return dict(as_of="2026-12-15T13:30:00+08:00", source="FUGLE",
        symbols={"2330":dict(name="example", bars_5m=bars(), bars_daily=bars(minutes=False))})

def test_3_models_never_authorize_orders():
    result=generate(payload())
    assert len(result["observations"])==3
    assert result["provider_response_verified"] is False
    assert result["model_training_status"]=="UNTRAINED_OR_UNVERIFIED"
    assert all(x["production_signal"] is False and x["order_authorized"] is False
        and x["trained_model_used"] is False and x["realized_net_pnl"] is None
        for x in result["observations"])

def test_missing_data_fails_closed():
    p=payload()
    p["symbols"]["2330"]["bars_daily"]=[]
    assert all(x["direction"]=="NO_TRADE" for x in generate(p)["observations"][1:])

def test_future_bar_fails_closed():
    p=payload()
    p["as_of"]="2026-11-05T09:10:00+08:00"
    assert all(x["direction"]=="NO_TRADE" for x in generate(p)["observations"])

def test_duplicate_timestamp_rejected():
    p=payload()
    b=p["symbols"]["2330"]["bars_5m"]
    b[3]["timestamp"]=b[2]["timestamp"]
    assert "unordered_or_duplicate_bars" in generate(p)["observations"][0]["rejection_reasons"]

def test_claimed_provider_enforced_not_certified():
    p=payload()
    p["source"]="UNVERIFIED"
    with pytest.raises(ValueError,match="unverified_source"):
        generate(p)

def test_deterministic_ids():
    a=generate(payload())["observations"]
    b=generate(payload())["observations"]
    assert [i["signal_id"] for i in a]==[i["signal_id"] for i in b]
