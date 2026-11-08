"""Fail-closed, actionable MCR research evidence gap report.

Engineering success, price-reference completeness, statistical eligibility and
formal trading approval are four *different* results. This module does not
guess prices or calculate fictitious trade P&L.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

SCHEMA="MCR_EVIDENCE_GAPS_V1"
MIN_FORWARD_DAYS=20
MIN_EVALUABLE_TRADES=200
MIN_REGIMES=2
MIN_OUTCOME_COMPLETENESS_PCT=95

def build_gap_report(episode,markout,calendar,*,latest_price_session=None):
    if episode.get("schema")!="MCR_EPISODE_AUDIT_V1" or markout.get("schema")!="MCR_EOD_MARKOUT_V1":
        raise ValueError("GAP_SOURCE_SCHEMA")
    if calendar.get("schema")!="MCR_SESSION_CALENDAR_V1":
        raise ValueError("GAP_CALENDAR_SCHEMA")
    if markout.get("asof_session")!=episode.get("last_session"):
        raise ValueError("GAP_SESSION_MISMATCH")
    if episode.get("episode_count")!=len(episode.get("episodes",[])):
        raise ValueError("GAP_EPISODE_COUNT_MISMATCH")
    if len(markout.get("results",[]))!=episode["episode_count"]:
        raise ValueError("GAP_MARKOUT_COUNT_MISMATCH")
    if episode.get("production_promotion_eligible") is not False or markout.get("trade_count")!=0:
        raise ValueError("UNVERIFIED_TRADING_CLAIM")
    if episode.get("cost_adjusted_expectancy_pct") is not None or markout.get("cost_adjusted_expectancy_pct") is not None:
        raise ValueError("UNVERIFIED_NET_EXPECTANCY")
    horizon_counts={str(h):sum(str(h) in r.get("horizons",{}) for r in markout["results"]) for h in (1,3,5,10)}
    event_states=Counter(r["status"] for r in markout["results"])
    gap_reasons=Counter()
    for r in markout["results"]:
        for why in r.get("horizon_gaps",{}).values():gap_reasons[why]+=1
    known_prices=calendar.get("exchange_sessions",{}).get("TWSE",[])
    known_sessions=len(known_prices)
    missing_gaps=calendar.get("unverified_weekday_gaps",[])
    missing_price=markout.get("source_price_rows",0)==0
    followup_day_count=max(0,known_sessions-1)
    future_reference_pct=round(100*horizon_counts["5"]/episode["episode_count"],2) if episode["episode_count"] else 0.0
    blockers=[
        {"key":"FORWARD_TRADING_DAYS","state":"INSUFFICIENT_DATA",
         "observed":followup_day_count,"required":MIN_FORWARD_DAYS,
         "deficit":max(0,MIN_FORWARD_DAYS-followup_day_count),
         "detail":"Verified EOD session coverage, not independent live signal days."},
        {"key":"EVALUABLE_EXECUTABLE_SAMPLES","state":"INSUFFICIENT_DATA",
         "observed":0,"required":MIN_EVALUABLE_TRADES,
         "deficit":MIN_EVALUABLE_TRADES,
         "detail":"Reference EOD observations are not executable trades."},
        {"key":"PIT_AND_EXECUTION","state":"NOT_VALIDATED",
         "detail":"Issuer availability, signal timestamp, spread, slippage and fills unverified."},
        {"key":"BASELINE_AND_REGIME","state":"NOT_EVALUABLE",
         "detail":"A/B/C/D controls, market regimes and walk-forward not proven."},
        {"key":"COST_ADJUSTED_EXPECTANCY","state":"NOT_EVALUABLE",
         "detail":"No verifiable fills or post-cost trade ledger."},
    ]
    if missing_gaps:
        blockers.insert(0,{"key":"UNVERIFIED_MARKET_SESSION_GAPS","state":"DATA_GAP",
              "dates":missing_gaps,"detail":"Verify actual exchange closure vs missing daily snapshot; no shifted outcomes."})
    if missing_price:
        blockers.insert(0,{"key":"OFFICIAL_EOD_REFERENCE_SOURCE","state":"DATA_GAP",
              "detail":"No verified source price rows; do not infer zero returns."})
    if latest_price_session and latest_price_session!=episode["last_session"]:
        blockers.insert(0,{"key":"FINANCING_PRICE_SESSION_MISMATCH","state":"DATA_GAP",
              "detail":"Latest captured official closing session differs from financing date.",
              "latest_price_session":latest_price_session})
    complete_5d_count=horizon_counts["5"]
    return {"schema":SCHEMA,"research_status":"INSUFFICIENT_DATA",
        "source_session":episode["last_session"],"observed_trading_sessions":episode["sessions"],
        "official_eod_snapshot_days":known_sessions,
        "raw_research_observations":episode["observation_rows"],
        "deduplicated_episodes":episode["episode_count"],
        "independent_executable_trades":0,
        "official_reference_price_rows":markout.get("source_price_rows",0),
        "forward_reference_completed_by_horizon":horizon_counts,
        "completed_5d_reference_count":complete_5d_count,
        "five_day_reference_coverage_pct":future_reference_pct,
        "outcome_state_counts":dict(event_states),
        "outcome_gap_reasons":dict(gap_reasons),
        "unverified_calendar_gap_dates":missing_gaps,
        "blockers":blockers,
        "minimum_gates":{"forward_days":MIN_FORWARD_DAYS,"evaluable_samples":MIN_EVALUABLE_TRADES,
           "regimes":MIN_REGIMES,"outcome_completeness_pct":MIN_OUTCOME_COMPLETENESS_PCT},
        "engineering_data_status":"DATA_GAP" if missing_gaps or missing_price or (latest_price_session and latest_price_session!=episode["last_session"]) else "PUBLISHED_EVIDENCE_VALIDATED",
        "counterfactual_abcd_status":"NOT_EVALUABLE",
        "cost_adjusted_expectancy_pct":None,"production_promotion_eligible":False,
        "requires_governance_approval":True,
        "notice":"This is an evidence sufficiency report, never a live buy/sell signal."}

def main():
    from research.mcr_session_calendar import build_calendar
    root=Path("research_output")
    e=json.loads((root/"mcr_episode_audit_latest.json").read_text(encoding="utf-8"))
    m=json.loads((root/"mcr_markout_latest.json").read_text(encoding="utf-8"))
    snaps=[]
    for p in sorted((root/"mcr_eod_price_evidence").glob("????-??-??.json")):
        d=json.loads(p.read_text(encoding="utf-8"))
        if d.get("session")!=p.stem:raise ValueError("PRICE_FILENAME_SESSION_MISMATCH")
        snaps.append(d)
    calendar=build_calendar(snaps)
    latest=snaps[-1]["session"] if snaps else None
    out=build_gap_report(e,m,calendar,latest_price_session=latest)
    (root/"mcr_evidence_gaps_latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("MCR_EVIDENCE_GATES",out["engineering_data_status"],out["research_status"],
          "priced",out["official_reference_price_rows"],"reference_5d_complete",out["completed_5d_reference_count"])
if __name__=="__main__":main()
