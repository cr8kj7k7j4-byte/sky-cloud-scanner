"""Strict session-aligned EOD markouts for MCR research observations.

Never infer an exchange trading session solely from symbol-level bars. A missing
quote must not silently extend a 1/3/5/10 exchange-session horizon.
Reference closes are NOT fills, investable returns, or net expectancy.
"""
from __future__ import annotations
from datetime import date,datetime
import json

HORIZONS=(1,3,5,10)
SOURCE_TYPES=("TWSE_OFFICIAL_DAILY","TPEX_OFFICIAL_DAILY","FUGLE_HISTORICAL_DAILY")

def _date(s):
    return date.fromisoformat(s)

def _price(p):
    if not isinstance(p,dict) or p.get("source") not in SOURCE_TYPES:
        raise ValueError("UNVERIFIED_PRICE_SOURCE")
    if p.get("exchange") not in ("TWSE","TPEx"):
        raise ValueError("INVALID_EXCHANGE")
    d=_date(p["session"])
    captured=datetime.fromisoformat(p["captured_at"])
    if captured.tzinfo is None or captured.date()<d:raise ValueError("MISSING_CAPTURE_PROVENANCE")
    close=p.get("close")
    if type(close) not in (int,float) or not 0<float(close)<100000:
        raise ValueError("INVALID_PRICE")
    if p.get("adjusted") is not False:raise ValueError("ADJUSTED_PRICE_UNSUPPORTED")
    return d,float(close)

def research_markouts(events,prices,*,asof_session,session_calendar=None):
    asof=_date(asof_session)
    if not isinstance(events,list) or not isinstance(prices,list):raise ValueError("BAD_RESEARCH_INPUT")
    indexed={}
    for p in prices:
        d,v=_price(p)
        if d>asof:raise ValueError("FUTURE_DATA_LEAK")
        key=(p["exchange"],p["symbol"],d.isoformat())
        if key in indexed:raise ValueError("DUPLICATE_PRICE_SESSION")
        indexed[key]=v

    calendar_valid=(isinstance(session_calendar,dict) and
                    session_calendar.get("schema")=="MCR_SESSION_CALENDAR_V1" and
                    session_calendar.get("source")=="VERIFIED_DUAL_MARKET_EOD_SNAPSHOTS")
    sessions={}
    gaps=set()
    if calendar_valid:
        gaps=set(session_calendar.get("unverified_weekday_gaps",[]))
        for m in ("TWSE","TPEx"):
            raw=session_calendar.get("exchange_sessions",{}).get(m,[])
            if not isinstance(raw,list) or raw!=sorted(set(raw)):
                raise ValueError("BAD_EXCHANGE_CALENDAR")
            if any(_date(s)>asof for s in raw):
                raise ValueError("FUTURE_CALENDAR_SESSION")
            sessions[m]=raw

    outputs=[]
    counts={"PENDING_FORWARD_SESSIONS":0,"MISSING_REFERENCE_PRICE":0,
        "MISSING_PRICE_ON_REQUIRED_SESSION":0,"UNVERIFIED_SESSION_GAP":0,
        "PENDING_SESSION_CALENDAR":0,"PARTIAL_REFERENCE_OUTCOMES":0}
    for event in events:
        if event.get("trade_eligible") is not False or event.get("candidate_signal_only") is not True:
            raise ValueError("UNAUTHORIZED_SIGNAL")
        first=_date(event["first_session"])
        market,sym=event["market"],event["symbol"]
        horizons={};gaps_by_horizon={}
        if not calendar_valid:
            status="PENDING_SESSION_CALENDAR"
        elif first>=asof:
            status="PENDING_FORWARD_SESSIONS"
        else:
            following=[d for d in sessions[market] if first<_date(d)<=asof]
            if not following:
                status="PENDING_FORWARD_SESSIONS"
            else:
                reference=following[0]
                ref_close=indexed.get((market,sym,reference))
                if ref_close is None:
                    status="MISSING_REFERENCE_PRICE"
                else:
                    reasons=[]
                    for h in HORIZONS:
                        if len(following)<=h:
                            gaps_by_horizon[str(h)]="PENDING_FORWARD_SESSIONS"
                            reasons.append("PENDING_FORWARD_SESSIONS")
                            continue
                        target=following[h]
                        # If any weekday between observation and target has no
                        # independently audited exchange-session evidence,
                        # reject the horizon instead of shifting prices.
                        if any(first<_date(g)<_date(target) for g in gaps):
                            gaps_by_horizon[str(h)]="UNVERIFIED_SESSION_GAP"
                            reasons.append("UNVERIFIED_SESSION_GAP")
                            continue
                        follow_close=indexed.get((market,sym,target))
                        if follow_close is None:
                            gaps_by_horizon[str(h)]="MISSING_PRICE_ON_REQUIRED_SESSION"
                            reasons.append("MISSING_PRICE_ON_REQUIRED_SESSION")
                            continue
                        horizons[str(h)]={
                            "reference_session":reference,"followup_session":target,
                            "reference_close":ref_close,"followup_close":follow_close,
                            "long_reference_change_pct":round(100*(follow_close/ref_close-1),4),
                            "outcome_kind":"EOD_REFERENCE_MARKOUT_NOT_EXECUTABLE",
                            "execution_validated":False,"cost_adjusted_pnl_pct":None}
                    if horizons:
                        status="PARTIAL_REFERENCE_OUTCOMES"
                    elif "UNVERIFIED_SESSION_GAP" in reasons:
                        status="UNVERIFIED_SESSION_GAP"
                    elif "MISSING_PRICE_ON_REQUIRED_SESSION" in reasons:
                        status="MISSING_PRICE_ON_REQUIRED_SESSION"
                    else:
                        status="PENDING_FORWARD_SESSIONS"
        counts[status]=counts.get(status,0)+1
        outputs.append({"episode_id":event["episode_id"],"status":status,
                        "horizons":horizons,"horizon_gaps":gaps_by_horizon,
                        "net_trade_expectancy_pct":None})
    n_complete=sum(len(r["horizons"]) for r in outputs)
    return {"schema":"MCR_EOD_MARKOUT_V1","asof_session":asof_session,
        "results":outputs,"source_price_rows":len(prices),
        "verified_session_calendar":calendar_valid,
        "session_calendar_coverage_days":session_calendar.get("coverage_days",0) if calendar_valid else 0,
        "unverified_session_gap_days":sorted(gaps) if calendar_valid else [],
        "reference_horizons_complete":n_complete,
        "outcome_status_counts":counts,
        "trade_count":0,"cost_adjusted_expectancy_pct":None,
        "report_status":"INSUFFICIENT_DATA","non_executable_reference":True}

def main():
    import argparse,pathlib
    from research.mcr_session_calendar import build_calendar
    p=argparse.ArgumentParser()
    p.add_argument("--episodes",default="research_output/mcr_episode_audit_latest.json")
    p.add_argument("--price-snapshot-dir",default="research_output/mcr_eod_price_evidence")
    p.add_argument("--asof",required=True)
    p.add_argument("--out",default="research_output/mcr_markout_latest.json")
    args=p.parse_args()
    events=json.loads(pathlib.Path(args.episodes).read_text(encoding="utf-8"))["episodes"]
    snapshots=[json.loads(p.read_text(encoding="utf-8")) for p in sorted(pathlib.Path(args.price_snapshot_dir).glob("????-??-??.json"))]
    calendar=build_calendar(snapshots)
    price_rows=[row for snap in snapshots for row in snap["rows"]]
    output=research_markouts(events,price_rows,asof_session=args.asof,session_calendar=calendar)
    dest=pathlib.Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print("MCR_MARKOUT",output["report_status"],"source_prices",len(price_rows),
          "horizons_completed",output["reference_horizons_complete"])

if __name__=="__main__":main()
