from __future__ import annotations

import pandas as pd

PRIMARY_COST_RATE = 0.0045
STRESS_COST_RATE = 0.0065
COST_MODEL_VERSION = "W2_FIXED_ROUND_TRIP_045_065_V1"
TOLERANCE_R = 1e-8


def _num(series, index):
    if series is None:
        return pd.Series(index=index,dtype=float)
    return pd.to_numeric(series, errors="coerce")


def apply_fixed_cost_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add/verify the W2 fixed round-trip cost scenarios.

    Scenario drag per share:
      0.45% primary = planned_entry * 0.0045
      0.65% stress  = planned_entry * 0.0065

    The drag is converted to R using original planned risk:
      planned_entry - planned_stop

    Required outcome evidence:
      gross_r_multiple OR outcome_exit_price OR actual_exit

    Existing net_r_045/net_r_065 values are preserved only when they agree
    with the deterministic calculation. A mismatch is marked CONFLICT and is
    never silently overwritten.

    These fields are post-feature research outcomes. They are not observed
    spread/slippage/fill evidence and must not enter decision-time features.
    """
    out=df.copy()
    entry=_num(out.get("planned_entry"), out.index)
    stop=_num(out.get("planned_stop"), out.index)
    risk=entry-stop

    if "gross_r_multiple" in out.columns:
        gross_r=_num(out["gross_r_multiple"], out.index)
    elif "outcome_exit_price" in out.columns:
        exit_px=_num(out["outcome_exit_price"], out.index)
        gross_r=(exit_px-entry)/risk.where(risk>0)
    elif "actual_exit" in out.columns:
        exit_px=_num(out["actual_exit"], out.index)
        gross_r=(exit_px-entry)/risk.where(risk>0)
    else:
        gross_r=pd.Series(index=out.index,dtype=float)

    valid=entry.gt(0) & risk.gt(0) & gross_r.notna()
    drag_045=(entry*PRIMARY_COST_RATE)/risk.where(risk>0)
    drag_065=(entry*STRESS_COST_RATE)/risk.where(risk>0)
    calc_045=(gross_r-drag_045).where(valid)
    calc_065=(gross_r-drag_065).where(valid)

    supplied_045=_num(out.get("net_r_045"), out.index)
    supplied_065=_num(out.get("net_r_065"), out.index)
    conflict_045=supplied_045.notna() & calc_045.notna() & ((supplied_045-calc_045).abs()>TOLERANCE_R)
    conflict_065=supplied_065.notna() & calc_065.notna() & ((supplied_065-calc_065).abs()>TOLERANCE_R)
    conflict=conflict_045 | conflict_065

    out["cost_model_version_fixed"]=COST_MODEL_VERSION
    out["gross_r_multiple"]=gross_r
    out["cost_drag_r_045"]=drag_045.where(valid)
    out["cost_drag_r_065"]=drag_065.where(valid)
    out["calculated_net_r_045"]=calc_045
    out["calculated_net_r_065"]=calc_065
    out["net_r_045"]=supplied_045.where(supplied_045.notna(),calc_045)
    out["net_r_065"]=supplied_065.where(supplied_065.notna(),calc_065)

    status=pd.Series("MISSING",index=out.index,dtype=object)
    status.loc[valid]="OK"
    status.loc[conflict]="CONFLICT"
    out["cost_scenario_status"]=status
    return out
