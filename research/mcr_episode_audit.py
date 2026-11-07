"""MCR research-only episode deduplication and selection-bias evidence audit.

Never alter immutable observation ledgers or call observation counts trades.
Episode cooldown is exploratory bookkeeping, not a tuned entry rule.
"""
from __future__ import annotations
import json
import hashlib
import math
from collections import Counter
from datetime import date
from pathlib import Path

VERSION="MCR_EPISODE_AUDIT_V1"
# Explicit, predeclared calendar cooldown; NOT an optimized trade rule.
EPISODE_GAP_CALENDAR_DAYS=7

def _date(x):
    return date.fromisoformat(x)

def validate_daily_ledger(doc):
    if doc.get("schema")!="MCR_PROXY_OBSERVATION_V1" or doc.get("research_only") is not True or doc.get("cannot_assume_pnl") is not True:
        raise ValueError("INVALID_LEDGER_CONTRACT")
    if doc.get("source_coverage")!="TWSE_TPEX_VERIFIED":raise ValueError("UNVERIFIED_UNIVERSE")
    day=_date(doc["session"])
    rows=doc.get("events")
    if not isinstance(rows,list) or len(rows)!=doc.get("total"):raise ValueError("TRUNCATED_LEDGER")
    seen=set()
    for r in rows:
        if r.get("source_session")!=day.isoformat() or r.get("execution_authorized") is not False:
            raise ValueError("INVALID_EVENT_PROVENANCE")
        market=r.get("market");sym=r.get("symbol")
        if market not in ("TWSE","TPEx") or not isinstance(sym,str) or len(sym)!=4 or not sym.isdigit():
            raise ValueError("INVALID_EVENT_IDENTITY")
        if r.get("outcome_evidence") is not None: raise ValueError("MUTATED_SOURCE_LEDGER")
        key=(market,sym)
        if key in seen:raise ValueError("DUPLICATE_DAILY_SYMBOL")
        seen.add(key)
    return day, rows

def build_episode_audit(daily_ledgers, *, source_merged=None):
    """One event episode per symbol unless >7 calendar days since last observation.
    Keep all observed days as raw observations, not independent trades.
    """
    if not daily_ledgers:raise ValueError("NO_LEDGER")
    docs=sorted(daily_ledgers,key=lambda d:d.get("session",""))
    sessions=[validate_daily_ledger(x)[0] for x in docs]
    if len(set(sessions))!=len(sessions):raise ValueError("DUPLICATE_SESSION")
    recent={};episodes=[];repeat=0
    per_day={}
    for doc in docs:
        day,rows=validate_daily_ledger(doc)
        per_day[day.isoformat()]=len(rows)
        for r in rows:
            market,symbol=r["market"],r["symbol"]
            key=(market,symbol)
            last=recent.get(key)
            if last and (day-last["last_day"]).days<=EPISODE_GAP_CALENDAR_DAYS:
                last["last_day"]=day
                last["n_observation_days"]+=1
                repeat+=1
                continue
            eid=hashlib.sha256(f"{VERSION}|{market}|{symbol}|{day.isoformat()}".encode()).hexdigest()
            episode={"episode_id":eid,"market":market,"symbol":symbol,"first_session":day.isoformat(),
                     "last_session":day.isoformat(),"observation_days":1,
                     "candidate_signal_only":True,"trade_eligible":False}
            episodes.append(episode)
            recent[key]={"last_day":day,"n_observation_days":1,"episode":episode}
    # Fill final episode end and observation count (never overwrites immutable daily events).
    for ep in episodes:
        state=next((v for k,v in recent.items() if v["episode"] is ep),None)
        if state:
            ep["last_session"]=state["last_day"].isoformat()
            ep["observation_days"]=state["n_observation_days"]
    raw=sum(per_day.values())
    if source_merged is not None:
        lastday=sessions[-1].isoformat()
        if source_merged.get("margin_data_date")!=lastday or source_merged.get("total")!=per_day[lastday]:
            raise ValueError("UNMATCHED_LATEST_UNIVERSE")
        candidates=source_merged["rows"]
        if len(candidates)!=source_merged["total"]:raise ValueError("TRUNCATED_PROXY_UNIVERSE")
        pct=[float(x["two_session_reduction_pct"]) for x in candidates]
        volume=[x.get("daily_volume_shares") for x in candidates]
        if any(not math.isfinite(x) or x<=0 for x in pct):raise ValueError("BAD_REDUCTION")
        # These bins are descriptive, not optimized filters.
        groups={
            "post_financing_balance_under_500_units":sum(x["margin_balance_current_units"]<500 for x in candidates),
            "reduction_at_least_20_pct":sum(x>=20 for x in pct),
            "volume_evidence_missing":sum(type(v) is not int or v<0 for v in volume),
            "volume_under_100000_shares":sum(type(v) is int and 0<=v<100000 for v in volume),
        }
        counts=Counter(x["exchange"] for x in candidates)
    else:
        groups=None;counts=None
    return {"schema":VERSION,"research_status":"INSUFFICIENT_DATA",
      "sessions":len(sessions),"first_session":sessions[0].isoformat(),
      "last_session":sessions[-1].isoformat(),"observation_rows":raw,
      "episode_count":len(episodes),"repeated_daily_observations":repeat,
      "episode_gap_calendar_days_fixed":EPISODE_GAP_CALENDAR_DAYS,
      "per_session_observation_counts":per_day,
      "latest_market_counts":dict(counts) if counts is not None else None,
      "bias_diagnostics":groups,"episodes":episodes,
      "independent_trade_sample_count":0,
      "future_outcome_complete_count":0,
      "cost_adjusted_expectancy_pct":None,
      "point_in_time_execution_validated":False,
      "universe_survivorship_audited":False,
      "baseline_comparison_status":"NOT_EVALUABLE_WITH_CURRENT_EVIDENCE",
      "production_promotion_eligible":False,
      "note":"This is a research episode audit, NOT transaction data or a profitability score."}

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--ledger-dir",default="research_output/mcr_event_ledger")
    parser.add_argument("--merged",default="research_output/mcr_official_proxy_combined_latest.json")
    parser.add_argument("--out",default="research_output/mcr_episode_audit_latest.json")
    args=parser.parse_args()
    files=sorted(Path(args.ledger_dir).glob("????-??-??.json"))
    docs=[json.loads(p.read_text(encoding="utf-8")) for p in files]
    source=json.loads(Path(args.merged).read_text(encoding="utf-8"))
    audit=build_episode_audit(docs,source_merged=source)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print("MCR_EPISODE_AUDIT",audit["research_status"],"daily_observations",audit["observation_rows"],
          "episodes",audit["episode_count"],"session_count",audit["sessions"])

if __name__=="__main__":main()
