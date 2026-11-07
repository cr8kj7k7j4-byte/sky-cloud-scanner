"""Append-only official EOD price evidence for future MCR episodes.

Read one TWSE and one TPEx close snapshot per day; never backdate a snapshot.
The point-in-time trading universe is the source's daily universe, not a 2026
current-universe reconstruction. Missing/suspended closes remain missing.
"""
from __future__ import annotations
import json
import math
import re
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo
from research.mcr_daily_volume import fetch, _date, SOURCES

TZ=ZoneInfo("Asia/Taipei")
COLUMNS={
    "TWSE":("Code","Date","ClosingPrice","TWSE_OFFICIAL_DAILY",500),
    "TPEx":("SecuritiesCompanyCode","Date","Close","TPEX_OFFICIAL_DAILY",300)
}
def _close(v):
    if isinstance(v,bool):return None
    s=str(v or "").strip().replace(",","")
    if s in ("","-","--","X","N/A"):return None
    try:
        result=float(s)
    except (ValueError,TypeError):return None
    return result if math.isfinite(result) and result>0 else None

def parse_market_rows(payload,market,*,captured_at):
    if market not in COLUMNS or not isinstance(payload,list) or len(payload)<300:
        raise ValueError("UNVERIFIED_DAILY_PRICE_UNIVERSE")
    stamp=datetime.fromisoformat(captured_at)
    if stamp.tzinfo is None:raise ValueError("CAPTURE_TIMEZONE_MISSING")
    code_key,date_key,close_key,label,min_rows=COLUMNS[market]
    seen=set();dates=set();result=[]
    for row in payload:
        if not isinstance(row,dict):raise ValueError("DAILY_PRICE_ROW_INVALID")
        if any(key not in row for key in (code_key,date_key,close_key)):
            raise ValueError("DAILY_PRICE_SCHEMA_MISMATCH")
        day=_date(row[date_key])
        dates.add(day)
        sym=str(row[code_key]).strip()
        if not re.fullmatch(r"[0-9]{4}",sym):continue
        if sym in seen:raise ValueError("DAILY_PRICE_DUPLICATE_STOCK")
        seen.add(sym)
        value=_close(row[close_key])
        if value is None:continue
        result.append({"source":label,"exchange":market,"symbol":sym,
          "session":day.isoformat(),"captured_at":captured_at,"close":value,"adjusted":False})
    if len(dates)!=1:raise ValueError("DAILY_PRICE_MIXED_DATES")
    session=next(iter(dates))
    if stamp.astimezone(TZ).date()<session:
        raise ValueError("CAPTURED_BEFORE_SOURCE_SESSION")
    if len(result)<min_rows:raise ValueError("DAILY_PRICE_COVERAGE_LOW")
    return session,result

def collect(target_session,*,fetcher=fetch,now=None):
    target=date.fromisoformat(target_session)
    now=now or datetime.now(TZ)
    if now.tzinfo is None:raise ValueError("CAPTURE_TIMEZONE_MISSING")
    records=[];counts={}
    for market in ("TWSE","TPEx"):
        day,items=parse_market_rows(fetcher(market),market,captured_at=now.isoformat())
        if day!=target:raise ValueError("PRICE_MARGIN_SESSION_MISMATCH")
        counts[market]=len(items)
        records.extend(items)
    if len({(r["exchange"],r["symbol"]) for r in records})!=len(records):
        raise ValueError("DUPLICATE_CROSS_MARKET_PRICE")
    records.sort(key=lambda r:(r["exchange"],r["symbol"]))
    return {"schema":"MCR_OFFICIAL_EOD_PRICES_V1","session":target_session,
       "recorded_at":now.isoformat(),"source_urls":SOURCES,
       "market_counts":counts,"total":len(records),"rows":records,
       "mode":"RESEARCH_REFERENCE_ONLY","execution_authorized":False,
       "historical_backfill":False,"provenance":"official_same_session_close"}

def write_immutable(snapshot,root="research_output/mcr_eod_price_evidence"):
    day=snapshot["session"]
    path=Path(root)/f"{day}.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        existing=json.loads(path.read_text(encoding="utf-8"))
        # A re-run must not silently overwrite historical observations or
        # recast old capture time. Compare non-capture price identity.
        def signature(doc):
            return {(r["exchange"],r["symbol"]):(r["session"],r["close"]) for r in doc["rows"]}
        if existing.get("schema")!=snapshot.get("schema") or existing.get("session")!=day or signature(existing)!=signature(snapshot):
            raise ValueError("IMMUTABLE_PRICE_SNAPSHOT_CONFLICT")
        return path
    path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return path

def main():
    source=json.loads(Path("research_output/mcr_official_proxy_combined_latest.json").read_text(encoding="utf-8"))
    if source.get("data_quality")!="BOTH_MARKETS_PASSED":
        raise ValueError("NO_VERIFIED_FINANCING_SESSION")
    snapshot=collect(source["margin_data_date"])
    path=write_immutable(snapshot)
    print("MCR_OFFICIAL_EOD_CAPTURED",path,snapshot["market_counts"],"count",snapshot["total"])

if __name__=="__main__":main()
