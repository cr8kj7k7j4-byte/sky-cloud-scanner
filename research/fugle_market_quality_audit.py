"""Independent Fugle paid market quality audit; never creates trading signals."""
import datetime as dt
import json
import os
import re
import statistics
import sys
import urllib.request
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from research.sky_fugle_atomic_ref_claim import guard_fugle_request

TZ = ZoneInfo("Asia/Taipei")
API = "https://api.fugle.tw/marketdata/v1.0/stock"
SOURCES = {"TSE": "https://isin.twse.com.tw/isin/e_C_public.jsp?strMode=2", "OTC": "https://isin.twse.com.tw/isin/e_C_public.jsp?strMode=4"}


class Rows(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.row=[]
        elif tag in ("td","th") and self.row is not None: self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ("td","th") and self.cell is not None:
            self.row.append("".join(self.cell).strip()); self.cell=None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row); self.row=None


def request(url, key=None):
    headers={"User-Agent":"Mozilla/5.0 Sky-ReadOnly-Audit", "Accept":"*/*"}
    if key:
        headers["X-API-KEY"]=key
        guard_fugle_request(url)
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=25) as res:
        return res.read(),res.headers.get_content_charset()


def official_codes(raw, charset):
    p=Rows(); p.feed(raw.decode(charset or "utf-8",errors="replace"))
    codes=set()
    for row in p.rows:
        if not row: continue
        match=re.match(r"^\s*(\d{4})\s+\S+",row[0])
        if match and any(c.strip().upper() == "ESVUFR" for c in row):
            codes.add(match.group(1))
    if len(codes)<100: raise ValueError("Official universe parsing produced fewer than 100 common equity symbols")
    return codes


def audit_status(coverage_status, in_session, live_freshness_status):
    """Snapshot freshness does not certify a current executed trade.

    Fugle Snapshot lastUpdated is snapshot time, not last execution time;
    a recent snapshot cannot authorize live trading decisions.
    """
    if coverage_status != "PASS":
        return "INSUFFICIENT_DATA_OR_REVIEW"
    if not in_session:
        return "COVERAGE_PASS_LIVE_PENDING"
    return ("SNAPSHOT_FRESH_EXECUTED_TRADE_UNVERIFIED"
            if live_freshness_status == "PASS" else "REVIEW_REQUIRED_LIVE")


def run():
    now=dt.datetime.now(TZ)
    report={"checked_at_taipei":now.isoformat(),"source":"Fugle / TWSE-hosted ISIN","classification":"READ_ONLY_RESEARCH_NO_TRADING","executed_trade_certified":False,"strategy_trade_authorized":False,"markets":{},"status":"INSUFFICIENT_DATA"}
    for market,url in SOURCES.items():
        result={"status":"INSUFFICIENT_DATA","official_count":None,"snapshot_count":None,"covered":None,"coverage_ratio":None,"missing_count":None,"issues":[]}
        official=None; quotes=None
        try:
            raw,charset=request(url); official=official_codes(raw,charset)
            result["official_count"]=len(official)
        except Exception as e: result["issues"].append("OFFICIAL_UNIVERSE_"+type(e).__name__)
        try:
            key=os.environ.get("FUGLE_API_KEY","")
            if not key: raise RuntimeError("Missing secret")
            raw,_=request(API+"/snapshot/quotes/"+market+"?type=COMMONSTOCK",key)
            body=json.loads(raw); quotes=body["data"]
            if body.get("market")!=market or not isinstance(quotes,list) or not quotes: raise ValueError("Malformed response")
            result["snapshot_count"]=len(quotes)
            symbols=[x.get("symbol") for x in quotes if isinstance(x,dict)]
            codes={x for x in symbols if isinstance(x,str) and re.fullmatch(r"\d{4}",x)}
            result["four_digit_snapshot_count"]=len(codes)
            result["duplicate_count"]=len(symbols)-len(set(symbols))
            result["missing_price_count"]=sum(1 for x in quotes if isinstance(x,dict) and x.get("closePrice") is None and x.get("lastPrice") is None)
            result["missing_volume_count"]=sum(1 for x in quotes if isinstance(x,dict) and x.get("tradeVolume") is None)
            result["type_mismatch_count"]=sum(1 for x in quotes if isinstance(x,dict) and x.get("type") != "EQUITY")
            result["response_date"]=body.get("date")
            ages=[]
            response_time=None
            try:
                clock=re.sub(r"[^0-9]", "", str(body.get("time","")))
                if len(clock)>=6:
                    response_time=dt.datetime.fromisoformat(str(body.get("date"))+"T"+clock[:2]+":"+clock[2:4]+":"+clock[4:6]).replace(tzinfo=TZ)
            except (ValueError,TypeError):
                pass
            result["response_age_seconds"]=round((now-response_time).total_seconds(),1) if response_time else None
            for x in quotes:
                if not isinstance(x,dict): continue
                stamp=x.get("lastUpdated")
                if isinstance(stamp,str):
                    try:
                        parsed=dt.datetime.fromisoformat(stamp.replace("Z","+00:00"))
                        if parsed.tzinfo is None: parsed=parsed.replace(tzinfo=TZ)
                        ages.append((now-parsed.astimezone(TZ)).total_seconds())
                    except ValueError: pass
                elif isinstance(stamp,(int,float)) and stamp>0:
                    seconds=stamp/(1e6 if stamp>1e14 else 1e3 if stamp>1e11 else 1)
                    ages.append((now-dt.datetime.fromtimestamp(seconds,TZ)).total_seconds())
            result["timestamp_count"]=len(ages)
            result["median_age_seconds"]=round(sorted(ages)[len(ages)//2],1) if ages else None
            result["max_age_seconds"]=round(max(ages),1) if ages else None
            if not all(isinstance(x,dict) for x in quotes): raise ValueError("Non-object snapshot entries")
            if official:
                missing=official-codes
                result["covered"]=len(official & codes)
                result["missing_count"]=len(missing)
                result["missing_sample"]=sorted(missing)[:30]
                result["coverage_ratio"]=round(result["covered"]/len(official),5)
                result["status"]="PASS" if result["coverage_ratio"]>=0.95 and result["duplicate_count"]==0 and result["missing_price_count"]==0 and result["missing_volume_count"]==0 and result["type_mismatch_count"]==0 else "REVIEW_REQUIRED"
            live=now.weekday()<5 and dt.time(9,5)<=now.time()<=dt.time(13,25)
            if live:
                result["live_freshness"]="PASS" if body.get("date")==now.date().isoformat() and ((result["response_age_seconds"] is not None and -30 <= result["response_age_seconds"] <= 120) or (ages and -30 <= statistics.median(ages) <= 120)) else "FAIL_OR_STALE"
                if result["live_freshness"]!="PASS": result["status"]="REVIEW_REQUIRED"
            else:
                result["live_freshness"]="NOT_TESTED_OUTSIDE_MARKET_HOURS"
        except Exception as e: result["issues"].append("FUGLE_"+type(e).__name__)
        report["markets"][market]=result
        # Safe diagnostic counters only; never print API keys, request headers or raw quotes.
        # A failing run must show which exact quality gate failed, not just REVIEW_REQUIRED.
        counters = {
            field: result.get(field)
            for field in ("duplicate_count", "missing_price_count", "missing_volume_count",
                          "type_mismatch_count", "missing_count", "response_date",
                          "response_age_seconds", "timestamp_count")
        }
        print(market, "status",result["status"],"official",result["official_count"],
              "snapshot",result["snapshot_count"],"coverage",result["coverage_ratio"],
              "freshness",result.get("live_freshness"),"counters",counters,
              "issues",result["issues"])
    report["coverage_status"]="PASS" if all(x["status"]=="PASS" for x in report["markets"].values()) else "INSUFFICIENT_DATA_OR_REVIEW"
    in_session=now.weekday()<5 and dt.time(9,5)<=now.time()<=dt.time(13,25)
    report["live_freshness_status"]=("PASS" if all(x.get("live_freshness")=="PASS" for x in report["markets"].values()) else "REVIEW_REQUIRED") if in_session else "NOT_TESTED_OUTSIDE_MARKET_HOURS"
    report["status"]=audit_status(report["coverage_status"], in_session, report["live_freshness_status"])
    with open("fugle_market_quality_audit.json","w") as f: json.dump(report,f,indent=2,ensure_ascii=False)
    print("OVERALL",report["status"])
    # Exit success only for fresh or historical snapshot-scope audit.
    # Neither path certifies executed trades or authorizes signals.
    if report["status"] not in ("SNAPSHOT_FRESH_EXECUTED_TRADE_UNVERIFIED", "COVERAGE_PASS_LIVE_PENDING"):
        sys.exit(1)


if __name__=="__main__": run()
