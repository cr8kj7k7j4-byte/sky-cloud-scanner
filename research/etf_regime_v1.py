"""ETF regime switching challenger: research only, not trade advice.
Precommitted 0050 60-session SMA and 20-session positive-return trigger;
next-session OPEN execution, 0.45/0.65% completed roundtrip stress.
No dividends, no fill/slippage proof, no live signals, no tuning.
"""
from __future__ import annotations
import argparse, json, os, time, math
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timezone
from pathlib import Path

DATA_URL = "https://api.finmindtrade.com/api/v4/data"
START = "2025-11-10"
END = "2026-11-06"
WARMUP_START = "2025-08-01"
SYMBOL = "0050"
MA = 60
MOM = 20
COSTS = (0.0045, 0.0065)


def fetch(token: str):
    args = urlencode({"dataset":"TaiwanStockPrice", "data_id":SYMBOL,
                      "start_date":WARMUP_START, "end_date":END})
    head={"User-Agent":"SkyETFRegimeResearch/1.0"}
    if token: head["Authorization"]="Bearer "+token
    try:
        with urlopen(Request(DATA_URL+"?"+args,headers=head),timeout=45) as r:
            reply=json.load(r)
        if reply.get("status") != 200 or not isinstance(reply.get("data"),list):
            return [], {"error":"API_RESPONSE", "msg":str(reply.get("msg"))[:150]}
        return reply["data"], {"status":200,"rows":len(reply["data"])}
    except Exception as exc:
        return [],{"error":type(exc).__name__+": "+str(exc)[:160]}


def prices(rows):
    out=[]
    for r in rows:
        try:
            d=str(r["date"]); op=float(r["open"]); cl=float(r["close"])
            if not (math.isfinite(op) and math.isfinite(cl) and op>0 and cl>0):continue
            out.append((d,op,cl))
        except (KeyError,TypeError,ValueError):continue
    return sorted({x[0]:x for x in out}.values())


def simulate(data,cost,mode):
    """A 1-unit investable sleeve, fractionally rebalanced; not brokerage fills."""
    cash=1.0; shares=0.0; nav=[]; transactions=[]; chosen=[]
    # Charge half roundtrip on BUY and SELL; never use future day's CLOSE
    for i,(d,op,cl) in enumerate(data):
        if i and d>=START:
            previous=i-1
            want=mode=="BUY_HOLD"
            if mode=="TREND" and previous>=MA-1:
                closes=[row[2] for row in data]
                ma=sum(closes[previous-MA+1:previous+1])/MA
                momentum=closes[previous]/closes[previous-MOM]-1
                want=closes[previous]>ma and momentum>0
            if mode=="TREND" and previous < MA-1:want=False
            if want and shares<=0:
                shares=cash/(op*(1+cost/2));cash=0
                transactions.append({"date":d,"side":"BUY","price":op})
            elif not want and shares>0:
                cash=shares*op*(1-cost/2);shares=0
                transactions.append({"date":d,"side":"SELL","price":op})
        if d>=START:
            net=cash+shares*cl
            nav.append((d,net))
            chosen.append(int(shares>0))
    if not nav:return {"n_days":0,"return_pct":None}
    # Unrealized remaining position is marked to market without simulated exit fees.
    peak=nav[0][1]; dd=0
    for _,value in nav:
        peak=max(peak,value);dd=min(dd,value/peak-1)
    return {"n_days":len(nav),"return_pct":round(100*(nav[-1][1]-1),4),
            "max_mark_to_market_drawdown_pct":round(100*dd,4),
            "entry_count":sum(x["side"]=="BUY" for x in transactions),
            "exit_count":sum(x["side"]=="SELL" for x in transactions),
            "invested_day_share_pct":round(100*sum(chosen)/len(chosen),2),
            "first_date":nav[0][0],"last_date":nav[-1][0],
            "ending_position_unrealized":bool(shares),
            "note":"Excludes ETF dividends, actual spread, market impact, stop losses; NAV is a research sleeve proxy"}


def run(token):
    rows, api=fetch(token)
    data=prices(rows)
    result={"model":"ETF_REGIME_TREND_CHALLENGER_V1",
            "status":"INSUFFICIENT_DATA",
            "production_signal":False,
            "window":[START,END],
            "underlying":SYMBOL,
            "raw_api":api,
            "valid_price_rows":len(data),
            "research_design":"60-session SMA + positive 20-session return, next day OPEN; compare buy and hold",
            "fixed_costs":list(COSTS),
            "is_fresh_oos":False,
            "results":{},
            "blockers":["Raw-price series lacks dividend-inclusive audited total return",
                        "May require corporate action / split audit and release timestamps",
                        "No independent OOS, live slippage, stop enforcement or capacity proof",
                        "One ETF and one year cannot establish stability, no Production access"]}
    if len(data)>=MA+30:
        for cost in COSTS:
            result["results"][str(cost)]={name:simulate(data,cost,name)
                              for name in ("TREND","BUY_HOLD")}
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="research_output/etf_regime_one_year.json")
    a=ap.parse_args()
    result=run(os.getenv("FINMIND_API_TOKEN",""))
    target=Path(a.out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({"status":result["status"],"api":result["raw_api"],
                      "valid_price_rows":result["valid_price_rows"],
                      "results":result["results"]},ensure_ascii=False))
