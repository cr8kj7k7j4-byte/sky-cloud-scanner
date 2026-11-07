"""Verified forward EOD price markouts for MCR observations, NOT trade fills.

Input price evidence has explicit symbol, exchange, date, source capture time and
official source; historical reconstruction cannot be mistaken for forward proof.
No trading expectancy until separately validated entry/fill/slippage rules exist.
"""
from __future__ import annotations
from datetime import date,datetime
import json

HORIZONS=(1,3,5,10)
SOURCE_TYPES=("TWSE_OFFICIAL_DAILY","TPEX_OFFICIAL_DAILY","FUGLE_HISTORICAL_DAILY")
def _as_date(s):
    return date.fromisoformat(s)
def _validated_price(p):
    if not isinstance(p,dict):raise ValueError("INVALID_PRICE_RECORD")
    if p.get("source") not in SOURCE_TYPES:raise ValueError("UNVERIFIED_PRICE_SOURCE")
    if p.get("exchange") not in ("TWSE","TPEx"):raise ValueError("INVALID_EXCHANGE")
    day=_as_date(p["session"])
    captured=datetime.fromisoformat(p["captured_at"])
    if captured.tzinfo is None:raise ValueError("MISSING_CAPTURE_TIMEZONE")
    if captured.date()<day:raise ValueError("IMPOSSIBLE_CAPTURE_TIME")
    close=p.get("close")
    if type(close) not in (int,float) or not (0<float(close)<100000):raise ValueError("INVALID_PRICE")
    if p.get("adjusted") is not False:raise ValueError("ADJUSTED_PRICE_UNSUPPORTED")
    return day,float(close)
def research_markouts(events,prices,*,asof_session):
    """Reference at FIRST session AFTER signal day; horizon by trading sessions.
    This is price-reference analysis, not transaction or fill performance.
    """
    asof=_as_date(asof_session)
    if not isinstance(prices,list):raise ValueError("INVALID_PRICES")
    indexed={}
    for p in prices:
        d,v=_validated_price(p)
        if d>asof:raise ValueError("FUTURE_DATA_LEAK")
        key=(p["exchange"],p["symbol"],d)
        if key in indexed:raise ValueError("DUPLICATE_PRICE_SESSION")
        indexed[key]=(v,p["source"],p["captured_at"])
    outputs=[]
    for event in events:
        if event.get("trade_eligible") is not False or event.get("candidate_signal_only") is not True:\n            raise ValueError("UNAUTHORIZED_SIGNAL")
        first=_as_date(event["first_session"])
        if first>=asof:
            outputs.append({"episode_id":event["episode_id"],"status":"PENDING_FORWARD_SESSIONS",
                            "horizons":{},"net_trade_expectancy_pct":None})
            continue
        key=(event["market"],event["symbol"])
        seq=sorted(((d,*val) for (m,s,d),val in indexed.items() if (m,s)==key and d>first),key=lambda x:x[0])
        horizons={}
        if not seq:
            status="PENDING_FORWARD_SESSIONS"
        else:
            # One-session-lag *reference* cannot assert an actual achievable entry price.
            entry=seq[0][1]
            for h in HORIZONS:
                # Closing h sessions after the first post-signal reference.
                if len(seq)<=h: continue
                later=seq[h]
                horizons[str(h)]={"reference_session":seq[0][0].isoformat(),
                    "followup_session":later[0].isoformat(),
                    "reference_close":entry,"followup_close":later[1],
                    "long_reference_change_pct":round(100*(later[1]/entry-1),4),
                    "outcome_kind":"EOD_REFERENCE_MARKOUT_NOT_EXECUTABLE",
                    "execution_validated":False,"cost_adjusted_pnl_pct":None}
            status="PARTIAL_REFERENCE_OUTCOMES" if horizons else "PENDING_FORWARD_SESSIONS"
        outputs.append({"episode_id":event["episode_id"],"status":status,
                        "horizons":horizons,"net_trade_expectancy_pct":None})
    return {"schema":"MCR_EOD_MARKOUT_V1","asof_session":asof_session,
            "results":outputs,
            "source_price_rows":len(prices),"trade_count":0,"cost_adjusted_expectancy_pct":None,
            "report_status":"INSUFFICIENT_DATA",
            "non_executable_reference":True}

def main():
    import argparse,pathlib
    p=argparse.ArgumentParser()
    p.add_argument("--episodes",default="research_output/mcr_episode_audit_latest.json")
    p.add_argument("--price-evidence",help="verified price evidence JSON list (no synthetic fills)")
    p.add_argument("--asof",required=True)
    p.add_argument("--out",default="research_output/mcr_markout_latest.json")
    args=p.parse_args()
    episodes=json.loads(pathlib.Path(args.episodes).read_text(encoding="utf-8"))["episodes"]
    prices=json.loads(pathlib.Path(args.price_evidence).read_text(encoding="utf-8")) if args.price_evidence else []
    report=research_markouts(episodes,prices,asof_session=args.asof)
    out=pathlib.Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("MCR_MARKOUT",report["report_status"],"price_rows",len(prices),"episode_count",len(episodes))

if __name__=="__main__":main()
