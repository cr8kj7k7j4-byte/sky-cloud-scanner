from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.outcome_engine import evaluate_shadow_long_path


def load_history_dir(path: str) -> dict[str,pd.DataFrame]:
    out={}
    for p in sorted(Path(path).glob("*_5.json")):
        obj=json.loads(p.read_text(encoding="utf-8"))
        symbol=str(obj.get("symbol") or p.name.split("_")[0])
        rows=[]
        for b in obj.get("data") or []:
            rows.append({
                "timestamp":b.get("date"),
                "open":b.get("open"),
                "high":b.get("high"),
                "low":b.get("low"),
                "close":b.get("close"),
                "volume":b.get("volume"),
            })
        df=pd.DataFrame(rows)
        if not df.empty:
            df["timestamp"]=pd.to_datetime(df["timestamp"],errors="coerce",utc=True)
            for c in ("open","high","low","close","volume"):
                df[c]=pd.to_numeric(df[c],errors="coerce")
            df=df.dropna(subset=["timestamp"]).sort_values("timestamp")
        out[symbol]=df
    return out


def _future_same_session(df: pd.DataFrame, decision_ts) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    ts=pd.to_datetime(decision_ts,errors="coerce",utc=True)
    if pd.isna(ts):
        return pd.DataFrame()
    session=ts.tz_convert("Asia/Taipei").date()
    local=df["timestamp"].dt.tz_convert("Asia/Taipei")
    return df[(df["timestamp"]>ts) & (local.dt.date==session)].copy()


def build_outcomes(
    decisions: pd.DataFrame,
    execution_context: pd.DataFrame,
    history: dict[str,pd.DataFrame],
) -> tuple[pd.DataFrame,dict]:
    """
    Construct conservative research-only counterfactual outcomes.

    Inputs are frozen before outcome construction:
      decision_id, symbol, decision_timestamp
      planned_entry, planned_stop, planned_target_1

    Only bars strictly AFTER decision_timestamp and on the same trading session
    are eligible. Same-bar stop+target ambiguity is resolved stop-first by the
    canonical outcome engine.

    No empirical fee/slippage/spread is invented here. Fixed 0.45/0.65 W2
    scenarios are applied later by intraday_pit_costs.py.
    """
    req_dec={"decision_id","symbol","decision_timestamp"}
    req_exec={"decision_id","planned_entry","planned_stop","planned_target_1"}
    if not req_dec.issubset(decisions.columns):
        raise ValueError(f"decisions missing {sorted(req_dec-set(decisions.columns))}")
    if not req_exec.issubset(execution_context.columns):
        raise ValueError(f"execution context missing {sorted(req_exec-set(execution_context.columns))}")
    if decisions["decision_id"].duplicated().any():
        raise ValueError("duplicate decision_id in decisions")
    if execution_context["decision_id"].duplicated().any():
        raise ValueError("duplicate decision_id in execution context")

    x=decisions[list(req_dec)].merge(
        execution_context[list(req_exec)],on="decision_id",how="left",validate="one_to_one"
    )
    rows=[]
    missing_history=0
    insufficient_future=0

    for _,r in x.iterrows():
        symbol=str(r["symbol"])
        h=history.get(symbol)
        future=_future_same_session(h,r["decision_timestamp"])
        if h is None or h.empty:
            missing_history+=1
        if future.empty:
            insufficient_future+=1

        bars=future[["high","low","close"]].to_dict("records") if not future.empty else []
        result=evaluate_shadow_long_path(
            entry=r.get("planned_entry"),
            stop=r.get("planned_stop"),
            target=r.get("planned_target_1"),
            bars=bars,
            fee_rate=None,
            tax_rate=None,
            entry_impact_rate=None,
            exit_impact_rate=None,
        )

        n=int(result.get("holding_bars") or 0)
        outcome_ts=None
        if n>0 and len(future)>=n:
            outcome_ts=future.iloc[n-1]["timestamp"].isoformat()

        status=result.get("status")
        gross_r=result.get("gross_r_multiple")
        rows.append({
            "decision_id":r["decision_id"],
            "outcome_status":"COMPLETE" if gross_r is not None else status,
            "fill_status":"COUNTERFACTUAL_ASSUMED_ENTRY" if gross_r is not None else "NOT_FILLED_OR_UNEVALUABLE",
            "actual_entry":None,
            "actual_exit":None,
            "outcome_exit_price":result.get("exit"),
            "gross_r_multiple":gross_r,
            "actual_entry_slippage_bps":None,
            "actual_exit_slippage_bps":None,
            "fees_twd":None,
            "tax_twd":None,
            "gross_pnl_twd":None,
            "net_pnl_twd":None,
            "r_multiple":gross_r,
            "mae_r":result.get("mae_r"),
            "mfe_r":result.get("mfe_r"),
            "holding_minutes":n*5 if n else None,
            "false_breakout":None,
            "missed_entry":None,
            "exit_reason":result.get("exit_reason"),
            "outcome_type":"COUNTERFACTUAL",
            "outcome_timestamp":outcome_ts,
            "outcome_path_policy":"SAME_SESSION_FUTURE_BARS_STOP_FIRST_V1",
            "same_bar_stop_target_ambiguous":result.get("ambiguous_same_bar"),
        })

    out=pd.DataFrame(rows)
    complete=float(out["gross_r_multiple"].notna().mean()) if len(out) else 0.0
    report={
        "schema_version":"INTRADAY_COUNTERFACTUAL_OUTCOME_V1_0",
        "rows":int(len(out)),
        "complete_gross_r_share":round(complete,6),
        "missing_history_rows":missing_history,
        "insufficient_future_rows":insufficient_future,
        "status":"PASS" if complete>=0.95 else "BLOCKED",
        "governance":{
            "outcome_type":"COUNTERFACTUAL",
            "bars_strictly_after_decision":True,
            "same_session_only":True,
            "same_bar_ambiguity":"STOP_FIRST",
            "empirical_execution_costs_invented":False,
            "false_breakout_definition_invented":False,
            "missed_entry_definition_invented":False,
        },
    }
    return out,report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--decisions",required=True)
    ap.add_argument("--execution-context",required=True)
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out-dir",default="research_output/intraday_counterfactual_outcomes")
    args=ap.parse_args()

    decisions=pd.read_csv(args.decisions)
    execution=pd.read_csv(args.execution_context)
    history=load_history_dir(args.history_dir)
    outcomes,report=build_outcomes(decisions,execution,history)

    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    outcomes.to_csv(out/"outcomes.csv",index=False)
    (out/"outcome_audit.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
