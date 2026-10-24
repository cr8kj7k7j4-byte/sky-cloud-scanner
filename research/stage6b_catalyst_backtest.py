from __future__ import annotations
import argparse, csv, json, re, time, statistics
from collections import defaultdict
from datetime import datetime, timedelta, time as dtime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from src.event_scoring import score_event

MOPS_HISTORY="https://mopsov.twse.com.tw/mops/web/t05st01"
UA={"User-Agent":"Mozilla/5.0 SkyResearch/1.0","Referer":"https://mopsov.twse.com.tw/mops/web/t05st01"}

def roc_y(d): return d.year-1911
def f(x,k):
    v=x.get(k); return None if v in (None,"") else float(v)
def dt(s): return datetime.fromisoformat(s)
def med(xs):
    xs=sorted(xs); n=len(xs)
    if not xs:return None
    return xs[n//2] if n%2 else (xs[n//2-1]+xs[n//2])/2

def fetch_company_year(sess, symbol, roc_year, retries=4):
    params={"step":"1","firstin":"true","year":str(roc_year),"co_id":symbol}
    err=None
    for k in range(retries):
        try:
            r=sess.get(MOPS_HISTORY,params=params,headers=UA,timeout=45)
            r.raise_for_status()
            return r.text
        except Exception as e:
            err=e; time.sleep(3*(k+1))
    raise RuntimeError(f"{symbol}/{roc_year}: {err}")

def normalize_mops_date(s):
    s=(s or "").strip().replace("年","/").replace("月","/").replace("日","")
    m=re.search(r"(\d{3,4})[/-](\d{1,2})[/-](\d{1,2})",s)
    if not m:return None
    y,mo,da=map(int,m.groups())
    if y<1911:y+=1911
    try:return datetime(y,mo,da).date()
    except:return None

def parse_company_year(html, symbol):
    if "查無資料" in html or "查無" in html:
        return []
    s=BeautifulSoup(html,"html.parser"); out=[]
    # First try visible result tables. Historical MOPS pages commonly include
    # columns such as 發言日期/時間、主旨、序號.
    for tb in s.find_all("table"):
        rows=tb.find_all("tr")
        if not rows: continue
        headers=[x.get_text(" ",strip=True) for x in rows[0].find_all(["th","td"])]
        header_txt="|".join(headers)
        if not any(k in header_txt for k in ["主旨","重大訊息","發言日期","發言時間"]):
            continue
        for tr in rows[1:]:
            cells=[x.get_text(" ",strip=True) for x in tr.find_all(["td","th"])]
            if len(cells)<3: continue
            joined=" | ".join(cells)
            dm=re.search(r"(\d{3,4}[/-]\d{1,2}[/-]\d{1,2})",joined)
            tm=re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?",joined)
            d=normalize_mops_date(dm.group(1)) if dm else None
            if not d: continue
            # Subject: choose the longest non-date/time text cell.
            texts=[x for x in cells if x and not re.fullmatch(r"[\d:/-]+",x)]
            subject=max(texts,key=len) if texts else joined
            out.append({"symbol":symbol,"name":"","announce_date":str(d),
                        "announce_time":tm.group(0).replace(":","") if tm else "",
                        "subject":subject,"seq":""})
    # Fallback: hidden input values used by detail links.
    if not out:
        for tr in s.find_all("tr"):
            vals=[str(i.get("value")).strip() for i in tr.find_all("input") if i.get("value") is not None]
            if not vals: continue
            joined=" | ".join(vals)
            if symbol not in vals and symbol not in joined: continue
            dm=re.search(r"(\d{7,8})",joined)
            tm=re.search(r"(?<!\d)(\d{6})(?!\d)",joined)
            d=None
            if dm:
                ds=dm.group(1)
                try:
                    if len(ds)==8: d=datetime.strptime(ds,"%Y%m%d").date()
                    elif len(ds)==7: d=datetime(int(ds[:3])+1911,int(ds[3:5]),int(ds[5:7])).date()
                except: d=None
            if not d: continue
            candidates=[v for v in vals if len(v)>=8 and not v.isdigit()]
            subject=max(candidates,key=len) if candidates else ""
            out.append({"symbol":symbol,"name":"","announce_date":str(d),
                        "announce_time":tm.group(1) if tm else "",
                        "subject":subject,"seq":""})
    seen=set(); ans=[]
    for x in out:
        key=(x["symbol"],x["announce_date"],x["announce_time"],x["subject"])
        if key not in seen:
            seen.add(key); ans.append(x)
    return ans

def group_days(obj):
    by=defaultdict(list)
    for b in obj["data"]:
        x={**b,"_dt":dt(b["date"])}
        by[x["_dt"].date()].append(x)
    for d in by: by[d].sort(key=lambda z:z["_dt"])
    return by

def action_day(event_date, event_time, days):
    ds=sorted(days)
    try: t=int(re.sub(r"\D","",event_time)[:4] or "9999")
    except: t=9999
    # Only pre-open announcements can be used same day; otherwise next trading day.
    if event_date in days and t<=830: return event_date
    return next((d for d in ds if d>event_date),None)

def detect_platform(bars,i):
    if i<4:return None
    prior=bars[i-4:i]; cur=bars[i]
    hs=[f(x,"high") for x in prior]; ls=[f(x,"low") for x in prior]; vs=[f(x,"volume") or 0 for x in prior]
    if any(v is None for v in hs+ls):return None
    ph,pl=max(hs),min(ls); mid=(ph+pl)/2
    cc=f(cur,"close"); cv=f(cur,"volume") or 0
    if not mid or not cc:return None
    width=(ph-pl)/mid*100
    vr=cv/(med(vs) or 1)
    risk=(cc-pl)/cc*100
    if width>1.5 or cc<=ph or vr<=1.5 or not (1.0<=risk<=2.5) or cc>100:return None
    return {"entry_signal":cc,"stop":pl,"risk_pct":risk,"volume_ratio":vr}

def simulate_next_open(bars,i,sig,target_r=2.0,cost_pct=.35,maxbars=24):
    if i+1>=len(bars):return None
    op=f(bars[i+1],"open")
    if op is None:return None
    # simple legal tick
    tick=.01 if op<10 else .05 if op<50 else .1 if op<100 else .5 if op<500 else 1 if op<1000 else 5
    entry=op+tick; stop=sig["stop"]
    if stop>=entry:return None
    risk=entry-stop; risk_pct=risk/entry*100
    if not (1.0<=risk_pct<=2.5):return None
    target=entry+target_r*risk
    end=min(len(bars)-1,i+1+maxbars)
    px=f(bars[end],"close"); reason="TIME"; mfe=-999; mae=999
    for j in range(i+2,end+1):
        hi,lo=f(bars[j],"high"),f(bars[j],"low")
        if hi is None or lo is None:continue
        mfe=max(mfe,(hi-entry)/risk); mae=min(mae,(lo-entry)/risk)
        sh=lo<=stop; th=hi>=target
        if sh and th: px=stop; reason="STOP_AMBIGUOUS"; break
        if sh: px=stop; reason="STOP"; break
        if th: px=target; reason="TP2R"; break
    gross=(px-entry)/risk
    net=gross-cost_pct/risk_pct
    return {"entry":entry,"stop":stop,"target":target,"risk_pct":risk_pct,"gross_r":gross,"net_r":net,
            "mfe_r":None if mfe==-999 else mfe,"mae_r":None if mae==999 else mae,"exit_reason":reason}

def metrics(rows):
    if not rows:return {"n":0}
    xs=[r["net_r"] for r in rows]; w=[x for x in xs if x>0]; l=[x for x in xs if x<0]
    gp=sum(w); gl=-sum(l)
    return {"n":len(xs),"win_rate":sum(x>0 for x in xs)/len(xs),"expectancy_r":statistics.mean(xs),
            "pf":gp/gl if gl else None}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",default="research/sky_100_manifest.json")
    ap.add_argument("--data-dir",default="research_data/history")
    ap.add_argument("--start",default="2025-01-01")
    ap.add_argument("--end",default="2026-10-22")
    ap.add_argument("--out",default="research_output_stage6b")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    mani=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    keep={str(x["symbol"]) for x in mani["sample"]}
    bysym={}
    for p in Path(args.data_dir).glob("*_5.json"):
        o=json.loads(p.read_text(encoding="utf-8"))
        if str(o["symbol"]) in keep: bysym[str(o["symbol"])]=group_days(o)

    sess=requests.Session()
    start_d=datetime.fromisoformat(args.start).date(); end_d=datetime.fromisoformat(args.end).date()
    events=[]; errors=[]
    years=range(start_d.year,end_d.year+1)
    for symbol in sorted(keep):
        for yy in years:
            try:
                es=parse_company_year(fetch_company_year(sess,symbol,yy-1911),symbol)
                for e in es:
                    ed=datetime.fromisoformat(e["announce_date"]).date()
                    if start_d<=ed<=end_d:
                        events.append({**e,"query_date":str(ed)})
            except Exception as e:
                errors.append({"symbol":symbol,"year":yy,"error":str(e)})
            time.sleep(.5)

    rows=[]
    for e in events:
        sym=e["symbol"]; by=bysym.get(sym)
        if not by: continue
        qd=datetime.fromisoformat(e["query_date"]).date()
        ad=action_day(qd,e.get("announce_time",""),set(by))
        if ad is None:continue
        bars=by[ad]
        pc=None
        prev=[x for x in sorted(by) if x<ad]
        if prev: pc=f(by[prev[-1]][-1],"close")
        if not pc:continue
        gap=(f(bars[0],"open")/pc-1)*100 if f(bars[0],"open") else None
        # first qualifying execution only; after 09:05, before 11:00
        for i,b in enumerate(bars):
            hm=b["_dt"].strftime("%H:%M")
            if hm<"09:05" or hm>"11:00": continue
            sig=detect_platform(bars,i)
            if not sig:continue
            sim=simulate_next_open(bars,i,sig)
            if sim:
                rows.append({**e,"action_date":str(ad),"trigger_time":hm,"gap_pct":gap,**sig,**sim})
            break

    # Event categories: descriptive only; no sentiment claim.
    cats={"EARNINGS":["財務","財報","盈餘","損益","自結"],
          "REVENUE":["營收","營業收入"],
          "GUIDANCE":["展望","預測","財測"],
          "CORPORATE_ACTION":["股利","增資","減資","合併","收購","處分","投資"],
          "INVESTOR_EVENT":["法人說明","法說"],
          "CONTRACT_ORDER":["訂單","合約","得標","契約"]}
    for r in rows:
        s=r["subject"]
        r["category"]=next((k for k,ws in cats.items() if any(w in s for w in ws)),"OTHER")
        r["event_type"]=r["category"]
        r["source"]="MOPS"
        r["event_role"]="CATALYST_EVIDENCE"
        score_now=datetime.fromisoformat(f'{r["action_date"]}T{r["trigger_time"]}:00')
        scored=score_event(r, now=score_now)
        r.update(scored)

    summary={"scope":"Stage6B true MOPS material-information event selection + platform execution",
             "period":[args.start,args.end],"events_found":len(events),"trade_rows":len(rows),
             "all":metrics(rows),"gap_ge_1":metrics([r for r in rows if r["gap_pct"] is not None and r["gap_pct"]>=1]),
             "by_category":{c:metrics([r for r in rows if r["category"]==c]) for c in sorted({r["category"] for r in rows})},
             "by_event_score_bucket":{
                 "80_100":metrics([r for r in rows if r.get("event_score",0)>=80]),
                 "60_79":metrics([r for r in rows if 60<=r.get("event_score",0)<80]),
                 "lt_60":metrics([r for r in rows if r.get("event_score",0)<60]),
             },
             "by_catalyst_score_bucket":{
                 "80_100":metrics([r for r in rows if r.get("catalyst_score",0)>=80]),
                 "60_79":metrics([r for r in rows if 60<=r.get("catalyst_score",0)<80]),
                 "lt_60":metrics([r for r in rows if r.get("catalyst_score",0)<60]),
             },
             "errors":errors[:50],
             "limitations":["MOPS historical page parsing can change; parsed rows are filtered to the fixed 100-symbol sample.",
                            "Material information is a catalyst-event selector, not a sentiment score.",
                            "Same-day use only when announcement time <=08:30; otherwise next trading day.",
                            "Execution is first qualifying platform breakout 09:05-11:00; next bar open +1 tick; stop-first ambiguity.",
                            "0.35% cost sensitivity; actual broker-specific cost remains to be calibrated.",
                            "Survivorship bias remains in the fixed current-listing sample."]}
    (out/"stage6b_report.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    if rows:
        fields=sorted({k for r in rows for k in r})
        with (out/"stage6b_trades.csv").open("w",newline="",encoding="utf-8-sig") as fh:
            w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(rows)
    if events:
        fields=sorted({k for r in events for k in r})
        with (out/"mops_events.csv").open("w",newline="",encoding="utf-8-sig") as fh:
            w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(events)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
