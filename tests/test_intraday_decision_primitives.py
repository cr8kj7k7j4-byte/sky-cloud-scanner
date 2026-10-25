from __future__ import annotations

import pandas as pd

from research.build_intraday_decision_primitives import build_primitives


def _bars():
    return pd.DataFrame([
        {
            "symbol":"1111",
            "timestamp":"2026-01-05T09:00:00+08:00",
            "session_date":"2026-01-05",
            "open":10.0,"high":10.2,"low":9.9,"close":10.1,
            "volume":100.0,"average":10.05,
        },
        {
            "symbol":"1111",
            "timestamp":"2026-01-05T09:05:00+08:00",
            "session_date":"2026-01-05",
            "open":10.1,"high":10.4,"low":10.0,"close":10.3,
            "volume":200.0,"average":10.2,
        },
        {
            "symbol":"1111",
            "timestamp":"2026-01-05T09:10:00+08:00",
            "session_date":"2026-01-05",
            "open":10.3,"high":99.0,"low":1.0,"close":50.0,
            "volume":9999.0,"average":50.0,
        },
    ])


def test_primitives_use_no_bar_after_decision_timestamp():
    decisions=pd.DataFrame([{
        "decision_id":"d1","symbol":"1111",
        "decision_timestamp":"2026-01-05T09:05:00+08:00",
        "session_date":"2026-01-05",
    }])
    frame,report=build_primitives(decisions,_bars())
    row=frame.iloc[0]
    assert row["feature_cutoff_timestamp"].startswith("2026-01-05T01:05:00")
    assert round(float(row["price"]),4)==10.1
    assert round(float(row["cumulative_vwap"]),4)==10.05
    assert round(float(row["price_vs_vwap_pct"]),4)==0.4975
    assert round(float(row["day_return_pct"]),4)==1.0
    assert round(float(row["session_high_at_decision"]),4)==10.2
    assert round(float(row["session_low_at_decision"]),4)==9.9
    assert row["source_bar_start_timestamp"].startswith("2026-01-05T01:00:00")
    assert report["status"]=="PASS"


def test_primitives_leave_frozen_alpha_fields_unset():
    decisions=pd.DataFrame([{
        "decision_id":"d1","symbol":"1111",
        "decision_timestamp":"2026-01-05T09:05:00+08:00",
        "session_date":"2026-01-05",
    }])
    frame,report=build_primitives(decisions,_bars())
    row=frame.iloc[0]
    assert row["frozen_alpha_status"]=="FROZEN_ALPHA_INPUT_REQUIRED"
    assert pd.isna(row["phase"])
    assert pd.isna(row["atr14"])
    assert pd.isna(row["rvol"])
    assert "phase" in report["intentionally_not_derived"]


def test_primitives_missing_when_no_predecision_bar():
    decisions=pd.DataFrame([{
        "decision_id":"d1","symbol":"1111",
        "decision_timestamp":"2026-01-05T08:55:00+08:00",
        "session_date":"2026-01-05",
    }])
    frame,report=build_primitives(decisions,_bars())
    assert frame.iloc[0]["primitive_status"]=="MISSING"
    assert report["status"]=="FAIL"


def test_primitives_include_bar_only_after_it_is_complete():
    decisions=pd.DataFrame([{
        "decision_id":"d1","symbol":"1111",
        "decision_timestamp":"2026-01-05T09:10:00+08:00",
        "session_date":"2026-01-05",
    }])
    frame,report=build_primitives(decisions,_bars())
    row=frame.iloc[0]
    assert row["feature_cutoff_timestamp"].startswith("2026-01-05T01:10:00")
    assert row["source_bar_start_timestamp"].startswith("2026-01-05T01:05:00")
    assert round(float(row["price"]),4)==10.3
    assert round(float(row["cumulative_vwap"]),4)==10.2
    assert round(float(row["session_high_at_decision"]),4)==10.4
    assert round(float(row["session_low_at_decision"]),4)==9.9
