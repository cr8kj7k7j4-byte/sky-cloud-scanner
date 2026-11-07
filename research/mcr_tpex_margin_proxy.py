"""TPEx official latest-session financing balance proxy. Research only; NOT 130% margin maintenance."""
from __future__ import annotations
import json, re
from datetime import date, datetime, timezone, timedelta
from urllib.request import Request, urlopen

SOURCE="https://www.tpex.org.tw/openapi/v1/tpex_mainboard_margin_balance"
DATE_KEYS=("資料日期","Date","date")
CODE_KEYS=("SecuritiesCompanyCode","代號","證券代號")
NAME_KEYS=("CompanyName","名稱","證券名稱")
BEFORE_KEYS=("MarginPurchaseBalancePreviousDay","前資餘額","融資前日餘額")
AFTER_KEYS=("MarginPurchaseBalance","資餘額","融資當日餘額")
MAX_BYTES=2_000_000
TW=timezone(timedelta(hours=8))

def source_fetch():
    req=Request(SOURCE,headers={"Accept":"application/json","User-Agent":"Mozilla/5.0 (compatible; SkyResearch/1.0)"})
    with urlopen(req,timeout=20) as r:
        raw=r.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError("TPEX_OVERSIZED_RESPONSE")
    return json.loads(raw)

def read_key(row, names):
    for key in names:
        if key in row: return row[key]
    raise ValueError("TPEX_REQUIRED_FIELD_MISSING_"+names[0])

def parse_date(value):
    value=str(value).strip().replace("/","-")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}",value): return date.fromisoformat(value)
    if re.fullmatch(r"\d{3}-\d{2}-\d{2}",value):
        return date.fromisoformat(str(int(value[:3])+1911)+value[3:])
    if re.fullmatch(r"\d{7}",value):
        return date(int(value[:3])+1911,int(value[3:5]),int(value[5:]))
    if re.fullmatch(r"\d{8}",value):
        return date(int(value[:4]),int(value[4:6]),int(value[6:]))
    raise ValueError("TPEX_UNRECOGNIZED_SESSION_DATE")

def number(value):
    if isinstance(value,bool): raise ValueError("TPEX_INVALID_NUMERIC")
    v=int(str(value).replace(",","").strip())
    if v<0: raise ValueError("TPEX_NEGATIVE_BALANCE")
    return v

def build_tpex_proxy(payload, *, now=None):
    if not isinstance(payload,list) or len(payload)<300: raise ValueError("TPEX_INCOMPLETE_UNIVERSE")
    now=now or datetime.now(TW)
    today=now.astimezone(TW).date()
    session=None
    seen=set(); result=[]
    for item in payload:
        if not isinstance(item,dict): raise ValueError("TPEX_NON_OBJECT_ROW")
        sid=str(read_key(item,CODE_KEYS)).strip()
        if not re.fullmatch(r"\d{4}",sid): continue
        if sid in seen: raise ValueError("TPEX_DUPLICATE_CODE")
        seen.add(sid)
        day=parse_date(read_key(item,DATE_KEYS))
        if session is None: session=day
        if session!=day: raise ValueError("TPEX_MIXED_DATES")
        prev=number(read_key(item,BEFORE_KEYS))
        curr=number(read_key(item,AFTER_KEYS))
        if prev<100 or curr<100 or curr>=prev: continue
        drop=round(100*(prev-curr)/prev,3)
        if drop<5: continue
        result.append({"stock_id":sid,"stock_name":str(read_key(item,NAME_KEYS)).strip()[:40],
           "exchange":"TPEx","margin_data_date":day.isoformat(),"two_session_reduction_pct":drop,
           "margin_balance_current_units":curr,"maintenance_below_130_verified":False,
           "net_expectancy_per_trade_pct":None,"trade_eligible":False,"action":"觀察"})
    if len(seen)<300: raise ValueError("TPEX_LOW_CODE_COVERAGE")
    if not session or session>today or (today-session).days>5:
        raise ValueError("TPEX_STALE_OR_FUTURE_DATE")
    result.sort(key=lambda r:(-r["two_session_reduction_pct"],-r["margin_balance_current_units"],r["stock_id"]))
    return {"mode":"RESEARCH_PROXY_ONLY","data_quality":"TPEX_PASSED","source":"TPEx",
       "coverage":"TPEX_ONLY","margin_data_date":session.isoformat(),
       "total":len(result),"rows":result,"no_trade_without_validation":True,
       "maintenance_below_130_verified":False,"observed_at":now.isoformat()}

def main():
    import pathlib
    out=pathlib.Path("research_output/mcr_tpex_proxy_audit.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    try:
        raw=source_fetch()
        if isinstance(raw,list) and raw and isinstance(raw[0],dict):
            print("TPEX_SOURCE_FIELD_NAMES:", sorted(raw[0].keys()))
            print("TPEX_SOURCE_ROW_COUNT:",len(raw))
        d=build_tpex_proxy(raw)
    except Exception as e:
        d={"mode":"RESEARCH_PROXY_ONLY","data_quality":"BLOCKED_EXTERNAL_DATA",
           "reason":type(e).__name__+":"+str(e)[:120],
           "source":"TPEx","total":None,"rows":[],"no_trade_without_validation":True}
    out.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
    print("TPEx MCR:",d["data_quality"],"total:",d["total"],"reason:",d.get("reason","none"))
    if d["data_quality"]!="TPEX_PASSED":raise SystemExit(2)

if __name__=="__main__": main()
