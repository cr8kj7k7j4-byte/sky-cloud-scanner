from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

SCHEMA_VERSION="INTRADAY_DECISION_PRIMITIVES_V1_0"


def load_history_dir(path: str) -> pd.DataFrame:
    rows=[]
    for p in sorted(Path(path).glob("*_5.json")):
        obj=json.loads(p.read_text(encoding="utf-8"))
        symbol=str(obj.get("symbol") or p.name.split("_")[0])
        for b in obj.get("data") or []:
            rows.append({
                "symbol":symbol,
                "timestamp":b.get("date"),
                "open":b.get("open"),
                "high":b.get("high"),
                "low":b.get("low"),
                "close":b.get("close"),
                "volume":b.get("volume"),
                "average":b.get("average"),
            })
    df=pd.DataFrame(rows)
    if df.empty:
        return df
    df["timestamp"]=pd.to_datetime(df["timestamp"],errors="coerce",utc=True)
    for c in ("open","high","low","close","volume","average"):
        df[c]=pd.to_numeric(df[c],errors="coerce")
    df=df[df["timestamp"].notna()].sort_values(["symbol","timestamp"])
    df["session_date"]=df["timestamp"].dt.tz_convert("Asia/Taipei").dt.date.astype(str)
    return df


def _bar_available_at(ts):
    return pd.to_datetime(ts,errors="coerce",utc=True) + pd.Timedelta(minutes=5)


def _cumulative_vwap_from_fugle(part: pd.DataFrame):
    # Fugle historical minute-candle "average" is already the cumulative
    # transaction average from market open. Do not volume-weight it again.
    if part.empty or "average" not in part.columns:
        return None
    s=pd.to_numeric(part["average"],errors="coerce").dropna()
    return float(s.iloc[-1]) if not s.empty else None


def build_primitives(decisions: pd.DataFrame,bars: pd.DataFrame) -> tuple[pd.DataFrame,dict]:
    d=decisions.copy()
    d["decision_timestamp"]=pd.to_datetime(d["decision_timestamp"],errors="coerce",utc=True)
    if "session_date" not in d.columns:
        d["session_date"]=d["decision_timestamp"].dt.tz_convert("Asia/Taipei").dt.date.astype(str)

    b=bars.copy()
    if b.empty:
        return pd.DataFrame(),{
            "schema_version":SCHEMA_VERSION,"status":"FAIL","reason":"NO_BARS","rows":0
        }
    b["timestamp"]=pd.to_datetime(b["timestamp"],errors="coerce",utc=True)
    if "session_date" not in b.columns:
        b["session_date"]=b["timestamp"].dt.tz_convert("Asia/Taipei").dt.date.astype(str)

    by_symbol=defaultdict(dict)
    for (symbol,day),part in b.groupby(["symbol","session_date"]):
        by_symbol[str(symbol)][str(day)]=part.sort_values("timestamp")

    out=[]; missing=0
    for _,row in d.iterrows():
        did=row["decision_id"]
        symbol=str(row["symbol"])
        day=str(row["session_date"])
        ts=row["decision_timestamp"]
        session=by_symbol.get(symbol,{}).get(day)
        if session is None or pd.isna(ts):
            out.append({"decision_id":did,"primitive_status":"MISSING"})
            missing+=1
            continue

        used=session[_bar_available_at(session["timestamp"])<=ts].copy()
        if used.empty:
            out.append({"decision_id":did,"primitive_status":"MISSING"})
            missing+=1
            continue

        last=used.iloc[-1]
        first=used.iloc[0]
        vwap=_cumulative_vwap_from_fugle(used)
        price=float(last["close"]) if pd.notna(last["close"]) else None
        session_low=float(used["low"].min()) if used["low"].notna().any() else None
        session_high=float(used["high"].max()) if used["high"].notna().any() else None
        session_open=float(first["open"]) if pd.notna(first["open"]) else None
        price_vs_vwap=((price/vwap)-1.0)*100.0 if price is not None and vwap not in (None,0) else None
        day_return=((price/session_open)-1.0)*100.0 if price is not None and session_open not in (None,0) else None
        session_position=(
            (price-session_low)/(session_high-session_low)
            if price is not None and session_low is not None and session_high is not None and session_high>session_low
            else None
        )

        prev_days=sorted(k for k in by_symbol.get(symbol,{}) if k<day)
        prev_close=None
        if prev_days:
            prev=by_symbol[symbol][prev_days[-1]]
            s=prev["close"].dropna()
            if not s.empty:
                prev_close=float(s.iloc[-1])
        gap=((session_open/prev_close)-1.0)*100.0 if session_open not in (None,0) and prev_close not in (None,0) else None

        # VWAP slope is intentionally derived only from cumulative VWAP snapshots.
        # It is a raw primitive, not a Production gate.
        vwap_slope=None
        if len(used)>=2:
            prev_used=used.iloc[:-1]
            prev_vwap=_cumulative_vwap_from_fugle(prev_used)
            if prev_vwap not in (None,0) and vwap is not None:
                vwap_slope=(vwap/prev_vwap)-1.0

        out.append({
            "decision_id":did,
            "feature_cutoff_timestamp":_bar_available_at(last["timestamp"]).isoformat(),
            "source_bar_start_timestamp":last["timestamp"].isoformat(),
            "entry_reference_price":price,
            "price":price,
            "volume":float(last["volume"]) if pd.notna(last["volume"]) else None,
            "cumulative_vwap":vwap,
            "price_vs_vwap_pct":price_vs_vwap,
            "vwap_slope":vwap_slope,
            "day_return_pct":day_return,
            "gap_pct":gap,
            "session_low_at_decision":session_low,
            "session_high_at_decision":session_high,
            "session_position":session_position,
            "primitive_status":"OK",
            # The following remain intentionally absent until exact frozen v1.4
            # definitions/inputs are available.
            "mtf_short_state":None,
            "mtf_mid_state":None,
            "mtf_long_state":None,
            "phase":None,
            "atr14":None,
            "price_extension_atr":None,
            "breakout_bar_atr":None,
            "rvol":None,
            "volume_zscore":None,
            "resistance_distance_pct":None,
            "stop_distance_pct":None,
            "stop_distance_atr":None,
            "frozen_alpha_status":"FROZEN_ALPHA_INPUT_REQUIRED",
        })

    result=pd.DataFrame(out)
    coverage=(result["primitive_status"]=="OK").mean() if len(result) else 0.0
    report={
        "schema_version":SCHEMA_VERSION,
        "rows":int(len(result)),
        "primitive_coverage":round(float(coverage),6),
        "missing_rows":missing,
        "status":"PASS" if coverage>=0.95 else "FAIL",
        "derived_fields":[
            "feature_cutoff_timestamp","entry_reference_price","price","volume",
            "cumulative_vwap","price_vs_vwap_pct","vwap_slope","day_return_pct",
            "gap_pct","session_low_at_decision","session_high_at_decision","session_position",
        ],
        "intentionally_not_derived":[
            "mtf_short_state","mtf_mid_state","mtf_long_state","phase","atr14",
            "price_extension_atr","breakout_bar_atr","rvol","volume_zscore",
            "resistance_distance_pct","stop_distance_pct","stop_distance_atr",
        ],
        "governance":{
            "bars_after_decision_used":False,
            "only_completed_5m_bars_used":True,
            "fugle_average_semantics":"CUMULATIVE_FROM_OPEN",
            "alpha_thresholds_invented":False,
            "research_only_strategy_substituted_for_v14":False,
        },
    }
    return result,report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--decisions",required=True)
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out-dir",default="research_output/intraday_decision_primitives")
    args=ap.parse_args()
    decisions=pd.read_csv(args.decisions)
    bars=load_history_dir(args.history_dir)
    frame,report=build_primitives(decisions,bars)
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/"feature_primitives.csv",index=False)
    (out/"feature_primitives_audit.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
