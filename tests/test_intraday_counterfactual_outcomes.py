from __future__ import annotations

import pandas as pd

from research.build_intraday_counterfactual_outcomes import build_outcomes


def test_counterfactual_outcome_uses_only_future_same_session_bars():
    decisions=pd.DataFrame([{
        "decision_id":"d1","symbol":"1111",
        "decision_timestamp":"2026-01-05T09:05:00+08:00",
    }])
    execution=pd.DataFrame([{
        "decision_id":"d1","planned_entry":10.0,
        "planned_stop":9.5,"planned_target_1":11.0,
    }])
    history={"1111":pd.DataFrame([
        {"timestamp":pd.Timestamp("2026-01-05T09:00:00+08:00"),"high":100.0,"low":1.0,"close":50.0},
        {"timestamp":pd.Timestamp("2026-01-05T09:10:00+08:00"),"high":10.5,"low":9.8,"close":10.4},
        {"timestamp":pd.Timestamp("2026-01-05T09:15:00+08:00"),"high":11.1,"low":10.2,"close":11.0},
        {"timestamp":pd.Timestamp("2026-01-06T09:00:00+08:00"),"high":20.0,"low":1.0,"close":15.0},
    ])}
    out,report=build_outcomes(decisions,execution,history)
    assert report["status"]=="PASS"
    assert out.loc[0,"outcome_type"]=="COUNTERFACTUAL"
    assert out.loc[0,"exit_reason"]=="TARGET"
    assert float(out.loc[0,"gross_r_multiple"])==2.0
    assert int(out.loc[0,"holding_minutes"])==10
    assert str(out.loc[0,"outcome_timestamp"]).startswith("2026-01-05")


def test_counterfactual_same_bar_stop_and_target_is_stop_first():
    decisions=pd.DataFrame([{
        "decision_id":"d1","symbol":"1111",
        "decision_timestamp":"2026-01-05T09:05:00+08:00",
    }])
    execution=pd.DataFrame([{
        "decision_id":"d1","planned_entry":10.0,
        "planned_stop":9.5,"planned_target_1":11.0,
    }])
    history={"1111":pd.DataFrame([
        {"timestamp":pd.Timestamp("2026-01-05T09:10:00+08:00"),"high":11.2,"low":9.4,"close":10.2},
    ])}
    out,report=build_outcomes(decisions,execution,history)
    assert report["status"]=="PASS"
    assert out.loc[0,"exit_reason"]=="STOP"
    assert bool(out.loc[0,"same_bar_stop_target_ambiguous"]) is True
    assert float(out.loc[0,"gross_r_multiple"])==-1.0


def test_counterfactual_missing_future_data_blocks_coverage():
    decisions=pd.DataFrame([{
        "decision_id":"d1","symbol":"1111",
        "decision_timestamp":"2026-01-05T09:05:00+08:00",
    }])
    execution=pd.DataFrame([{
        "decision_id":"d1","planned_entry":10.0,
        "planned_stop":9.5,"planned_target_1":11.0,
    }])
    out,report=build_outcomes(decisions,execution,{})
    assert report["status"]=="BLOCKED"
    assert report["complete_gross_r_share"]==0.0
    assert pd.isna(out.loc[0,"gross_r_multiple"])
    assert pd.isna(out.loc[0,"false_breakout"])
    assert pd.isna(out.loc[0,"missed_entry"])
