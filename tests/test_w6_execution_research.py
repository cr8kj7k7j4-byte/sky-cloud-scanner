from research.w6_execution_baseline import (
    classify_price_bucket,
    classify_time_bucket,
    spread_bps,
    W6L1ExecutionSample,
    aggregate_fill_rates,
)
from research.w6_execution_evidence import (
    decision_to_w6_evidence,
    paper_snapshot_to_w6_evidence,
    summarize_p1,
)
from datetime import datetime
from zoneinfo import ZoneInfo


TZ = ZoneInfo("Asia/Taipei")


def test_fixed_time_buckets():
    assert classify_time_bucket(datetime(2026,10,26,9,4,tzinfo=TZ)) == "09:00-09:05"
    assert classify_time_bucket(datetime(2026,10,26,9,5,tzinfo=TZ)) == "09:05-09:15"
    assert classify_time_bucket(datetime(2026,10,26,10,15,tzinfo=TZ)) == "10:15+"


def test_price_buckets():
    assert classify_price_bucket(19.9) == "<20"
    assert classify_price_bucket(20) == "20-50"
    assert classify_price_bucket(50) == "50-100"
    assert classify_price_bucket(100.1) == ">100_RESEARCH_ONLY"


def test_spread_bps_is_reference_not_fill():
    out = spread_bps(50.0, 50.1)
    assert out is not None and out > 0


def test_unknown_fill_is_not_counted_as_zero_fill_rate():
    sample = W6L1ExecutionSample(
        symbol="2409",
        observation_timestamp="2026-10-26T09:05:00+08:00",
        execution_type="QUOTE_ONLY",
        reference_price=50.0,
        bid=49.95,
        ask=50.05,
        fill_status="UNKNOWN",
    )
    out = aggregate_fill_rates([sample])
    assert out["sample"] == 0
    assert out["unknown_sample"] == 1
    assert out["fill_rate"] is None


def test_non_fill_cannot_keep_fill_price():
    row = decision_to_w6_evidence({
        "record_id": "r1",
        "run_id": "run1",
        "symbol": "2409",
        "observed_at": "2026-10-26T09:05:00+08:00",
        "market": {"last": 50.0, "bid": 49.95, "ask": 50.05},
        "plan": {"entry": 50.0, "stop": 49.5},
        "execution": {"fill_status": "MISSED", "fill_price": 50.1},
    })
    assert row["fill_status"] == "MISSED"
    assert row["fill_price"] is None


def test_paper_snapshot_maps_l1_without_inventing_fill():
    row = paper_snapshot_to_w6_evidence({
        "run_id": "run1",
        "symbol": "2409",
        "observation_timestamp": "2026-10-26T09:05:00+08:00",
        "assumed_entry": 50.0,
        "risk_per_share": 0.5,
        "market": {
            "last": 50.0,
            "bid": 49.95,
            "ask": 50.05,
            "l1_quote_time": 123456789,
            "l1_quote_source": "FUGLE_INTRADAY_QUOTE",
        },
    })
    assert row["bid"] == 49.95
    assert row["ask"] == 50.05
    assert row["fill_status"] == "UNKNOWN"
    assert row["fill_price"] is None


def test_adverse_selection_only_for_fill():
    s = W6L1ExecutionSample(
        symbol="2409",
        observation_timestamp="2026-10-26T09:05:00+08:00",
        execution_type="AGGRESSIVE_LIMIT",
        reference_price=50.0,
        bid=49.95,
        ask=50.05,
        fill_status="FILLED",
        fill_price=50.05,
        risk_per_share=0.5,
        future_price_1m=49.9,
    )
    m = s.metrics()
    assert m["adverse_selection_1m"] is True


def test_twenty_quote_only_rows_can_ready_spread_not_slippage():
    rows = []
    for i in range(20):
        rows.append({
            "symbol": str(2400 + i),
            "observation_timestamp": "2026-10-26T09:05:00+08:00",
            "execution_type": "QUOTE_ONLY",
            "reference_price": 50.0,
            "bid": 49.95,
            "ask": 50.05,
            "fill_status": "UNKNOWN",
            "risk_per_share": 0.5,
        })
    out = summarize_p1(rows)
    assert out["spread_status"] == "BASELINE_READY"
    assert out["slippage_status"] == "INSUFFICIENT_DATA"
    assert out["status"] == "INSUFFICIENT_DATA"
    assert out["fill_rate"] is None


def test_p1_requires_observed_slippage_sufficiency():
    rows = [{
        "symbol": "2409",
        "observation_timestamp": "2026-10-26T09:05:00+08:00",
        "execution_type": "AGGRESSIVE_LIMIT",
        "reference_price": 50.0,
        "bid": 49.95,
        "ask": 50.05,
        "fill_status": "FILLED",
        "fill_price": 50.05,
        "risk_per_share": 0.5,
    }]
    out = summarize_p1(rows)
    assert out["status"] == "INSUFFICIENT_DATA"
    assert out["sample"] == 1
