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
    quote_time_integrity,
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
            "quote_source": "FUGLE_INTRADAY_QUOTE",
            "quote_timestamp": "2026-10-26T09:05:00+08:00",
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


def test_w6_quote_evidence_preserves_observation_identity_not_execution_claim():
    from research.w6_execution_evidence import paper_snapshot_to_w6_evidence
    row = paper_snapshot_to_w6_evidence({
        "record_id": "canonical-r1", "observation_record_id": "canonical-r1",
        "decision_id": None, "decision_provenance_status": "RANKING_OBSERVATION_ONLY",
        "run_id": "r1", "symbol": "2330",
        "observed_at": "2026-11-04T09:05:00+08:00",
        "market": {"last": 50.0, "bid": 49.9, "ask": 50.1},
    })
    assert row["record_id"] == "canonical-r1"
    assert row["observation_record_id"] == "canonical-r1"
    assert row["decision_id"] is None
    assert row["decision_provenance_status"] == "RANKING_OBSERVATION_ONLY"
    assert row["fill_status"] == "UNKNOWN"
    assert row["fill_price"] is None

def test_w6_microsecond_quote_after_scan_is_not_retroactive():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    quote_microseconds = int(datetime(2026, 10, 28, 9, 53, tzinfo=ZoneInfo("Asia/Taipei")).timestamp() * 1_000_000)
    row = {
        "symbol": "2409", "observation_timestamp": "2026-10-28T09:51:00+08:00",
        "quote_timestamp": quote_microseconds, "quote_source": "FUGLE_INTRADAY_QUOTE",
        "bid": 49.95, "ask": 50.05, "reference_price": 50.0,
        "fill_status": "UNKNOWN", "execution_type": "QUOTE_ONLY",
    }
    quality = quote_time_integrity(row)
    assert quality["quote_after_scan_observation"]
    assert not quality["quote_spread_time_valid"]
    assert not quality["decision_time_quote_valid"]
    out = summarize_p1([dict(row, symbol=str(2400 + i)) for i in range(20)])
    assert out["spread_status"] == "INSUFFICIENT_DATA"
    assert out["quote_after_scan_observation_count"] == 20
    assert out["spread_sample_count"] == 0


def test_w6_quote_acquisition_can_establish_quote_spread_not_decision_quote():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    quote_microseconds = int(datetime(2026, 10, 28, 9, 53, tzinfo=ZoneInfo("Asia/Taipei")).timestamp() * 1_000_000)
    row = {
        "symbol": "2409", "observation_timestamp": "2026-10-28T09:51:00+08:00",
        "quote_observation_timestamp": "2026-10-28T09:53:01+08:00",
        "quote_timestamp": quote_microseconds, "quote_source": "FUGLE_INTRADAY_QUOTE",
        "bid": 49.95, "ask": 50.05, "reference_price": 50.0,
        "fill_status": "UNKNOWN", "execution_type": "QUOTE_ONLY",
    }
    quality = quote_time_integrity(row)
    assert quality["quote_spread_time_valid"]
    assert not quality["decision_time_quote_valid"]
    out = summarize_p1([dict(row, symbol=str(2400 + i)) for i in range(20)])
    assert out["spread_status"] == "BASELINE_READY"
    assert out["decision_time_quote_valid_count"] == 0
    assert out["fill_evaluable_sample"] == 0


def test_w6_invalid_time_and_missing_source_fail_closed():
    row = {
        "observation_timestamp": "2026-10-28T09:51:00+08:00",
        "quote_observation_timestamp": "2026-10-28T09:53:01+08:00",
        "quote_timestamp": "2026-10-28T09:53:00",  # timezone-naive
        "quote_source": "",
    }
    quality = quote_time_integrity(row)
    assert not quality["quote_spread_time_valid"]
    assert not quality["quote_timestamp_valid"]

def test_w6_invalid_acquisition_time_cannot_fallback_to_scan_time():
    row = {
        "observation_timestamp": "2026-10-28T09:53:01+08:00",
        "quote_observation_timestamp": "bad-timestamp",
        "quote_timestamp": "2026-10-28T09:53:00+08:00",
        "quote_source": "FUGLE_INTRADAY_QUOTE",
    }
    quality = quote_time_integrity(row)
    assert not quality["quote_spread_time_valid"]
    assert quality["decision_time_quote_valid"]
