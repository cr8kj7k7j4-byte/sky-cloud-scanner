from __future__ import annotations

import pandas as pd

PRIMARY_COST_RATE = 0.0045
STRESS_COST_RATE = 0.0065
COST_MODEL_VERSION = "W2_FIXED_ROUND_TRIP_045_065_V1"


def _num(series):
    return pd.to_numeric(series, errors="coerce")


def apply_fixed_cost_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add W2 fixed round-trip cost scenario fields without changing Alpha logic.

    The cost stress is modeled as a total round-trip drag equal to
    entry_reference * scenario_rate.  It is converted into R by dividing by
    the original per-share risk (planned_entry - planned_stop).

    Required inputs:
      planned_entry
      planned_stop
      gross_r_multiple OR outcome_exit_price

    This is a deterministic research cost scenario, not an observed broker fee,
    spread, slippage, or fill record.
    """
    out=df.copy()
    entry=_num(out.get("planned_entry", pd.Series(index=out.index,dtype=float)))
    stop=_num(out.get("planned_stop", pd.Series(index=out.index,dtype=float)))
    risk=entry-stop

    if "gross_r_multiple" in out.columns:
        gross_r=_num(out["gross_r_multiple"])
    elif "outcome_exit_price" in out.columns:
        exit_px=_num(out["outcome_exit_price"])
        gross_r=(exit_px-entry)/risk.where(risk>0)
    elif "actual_exit" in out.columns:
        exit_px=_num(out["actual_exit"])
        gross_r=(exit_px-entry)/risk.where(risk>0)
    else:
        gross_r=pd.Series(index=out.index,dtype=float)

    valid=entry.gt(0) & risk.gt(0) & gross_r.notna()
    drag_045=(entry*PRIMARY_COST_RATE)/risk.where(risk>0)
    drag_065=(entry*STRESS_COST_RATE)/risk.where(risk>0)

    out["cost_model_version_fixed"]=COST_MODEL_VERSION
    out["gross_r_multiple"]=gross_r
    out["cost_drag_r_045"]=drag_045.where(valid)
    out["cost_drag_r_065"]=drag_065.where(valid)
    out["net_r_045"]=(gross_r-drag_045).where(valid)
    out["net_r_065"]=(gross_r-drag_065).where(valid)
    out["cost_scenario_status"]=valid.map({True:"OK",False:"MISSING"})
    return out
