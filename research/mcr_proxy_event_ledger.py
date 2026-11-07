"""Daily immutable point-in-time MCR proxy observation ledger. No trades or fill simulation."""
import hashlib
import json
from pathlib import Path

SCHEMA="MCR_PROXY_OBSERVATION_V1"

def build_events(merged):
    if merged.get("coverage")!="TWSE_TPEX_VERIFIED" or merged.get("data_quality")!="BOTH_MARKETS_PASSED":
        raise ValueError("UNVERIFIED_SOURCE")
    day=merged.get("margin_data_date")
    rows=merged.get("rows")
    if not isinstance(rows,list) or merged.get("total")!=len(rows) or not day:
        raise ValueError("INCOMPLETE_SOURCE")
    events=[]
    for row in rows:
        if row.get("margin_data_date")!=day or row.get("trade_eligible") is not False:
            raise ValueError("INVALID_EVENT_SOURCE")
        symbol=row["stock_id"]
        market=row["exchange"]
        event_id=hashlib.sha256(f"{SCHEMA}|{day}|{market}|{symbol}".encode()).hexdigest()
        events.append({
            "event_id":event_id,"schema":SCHEMA,"symbol":symbol,
            "market":market,"source_session":day,
            "source":"TWSE" if market=="TWSE" else "TPEx",
            "source_evidence_kind":"OFFICIAL_EOD_FINANCING_BALANCE",
            "balance_reduction_pct":row["two_session_reduction_pct"],
            "balance_units":row["margin_balance_current_units"],
            "signal_kind":"RESEARCH_OBSERVATION_ONLY",
            "direction":None,"entry":None,"stop":None,"targets":None,
            "execution_authorized":False,"estimated_maintenance_below_130":None,
            "outcome_status":"PENDING_FORWARD_PRICE_EVIDENCE",
            "outcome_evidence":None
        })
    if len({e["event_id"] for e in events})!=len(events):
        raise ValueError("DUPLICATE_EVENT_ID")
    return {"schema":SCHEMA,"session":day,
            "source_coverage":"TWSE_TPEX_VERIFIED",
            "total":len(events),"events":events,
            "research_only":True,"cannot_assume_pnl":True}

def write_immutable(merged, root="research_output/mcr_event_ledger"):
    feed=build_events(merged)
    path=Path(root)/f"{feed['session']}.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    canonical=json.dumps(feed,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    if path.exists():
        if path.read_text(encoding="utf-8")!=canonical:
            raise ValueError("EXISTING_EVENT_LEDGER_CONFLICT")
        return path
    path.write_text(canonical,encoding="utf-8")
    return path

if __name__=="__main__":
    merged=json.loads(Path("research_output/mcr_official_proxy_combined_latest.json").read_text(encoding="utf-8"))
    p=write_immutable(merged)
    print("MCR_EVENTS_WRITTEN",p)
