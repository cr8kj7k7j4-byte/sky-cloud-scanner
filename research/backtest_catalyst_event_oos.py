from __future__ import annotations
import argparse,csv,json,re,time,math,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

MOPS_HISTORY="https://mopsov.twse.com.tw/mops/web/t05st01"
UA={"User-Agent":"Mozilla/5.0 SkyResearch/1.0","Referer":MOPS_HISTORY}
COSTS=[0.00,0.10,0.20,0.25,0.35]
HORIZONS={"30m":5,"60m":11,"120m":23}

def fnum(x):
    try:
        if x in (None,""): return None
        return float(str(x).replace(",",""))
    except Exception:
        return None

def normalize_date(s):
    s=(s or "").strip().replace("年","/").replace("月","/").replace("日","")
    m=re.search(r"(\d{3,4})[/-](\d{1,2})[/-](\d{1,2})",s)
    if not m:return None
    y,mo,da=map(int,m.groups())
    if y<1911:y+=1911
    try:return datetime(y,mo,da).date()
    except:return None

def fetch_company_year(sess,symbol,roc_year,retries=3):
    params={"step":"1","firstin":"true","year":str(roc_year),"co_id":symbol}
    err=None
    for k in range(retries):
        try:
            r=sess.get(MOPS_HISTORY,params=params,headers=UA,timeout=45)
            r.raise_for_status()
            return r.text
        except Exception as e:
            err=e; time.sleep(2*(k+1))
    raise RuntimeError(f"{symbol}/{roc_year}: {err}")

def parse_company_year(html,symbol):
    if "查無資料" in html or "查無" in html:return []
    s=BeautifulSoup(html,"html.parser"); out=[]
    for tb in s.find_all("table"):
        rows=tb.find_all("tr")
        if not rows: continue
        headers=[x.get_text(" ",strip=True) for x in rows[0].find_all(["th","td"])]
        head="|".join(headers)
        if not any(k in head for k in ["主旨","重大訊息","發言日期","發言時間"]):continue
        for tr in rows[1:]:
            cells=[x.get_text(" ",strip=True) for x in tr.find_all(["td","th"])]
            if len(cells)<3:continue
            joined=" | ".join(cells)
            dm=re.search(r"(\d{3,4}[/-]\d{1,2}[/-]\d{1,2})",joined)
            tm=re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?",joined)
            d=normalize_date(dm.group(1)) if dm else None
            if not d:continue
            texts=[x for x in cells if x and not re.fullmatch(r"[\d:/-]+",x)]
            subject=max(texts,key=len) if texts else joined
            out.append({"symbol":symbol,"announce_date":str(d),
                        "announce_time":tm.group(0) if tm else "",
                        "subject":subject})
    seen=set(); ans=[]
    for x in out:
        key=(x["symbol"],x["announce_date"],x["announce_time"],x["subject"])
        if key not in seen:
            seen.add(key); ans.append(x)
    return ans

def category(subject):
    cats={
      "EARNINGS":["財務","財報","盈餘","損益","自結"],
      "REVENUE":["營收","營業收入"],
      "GUIDANCE":["展望","預測","財測"],
      "CORPORATE_ACTION":["股利","增資","減資","合併","收購","處分","投資"],
      "INVESTOR_EVENT":["法人說明","法說"],
      "CONTRACT_ORDER":["訂單","合約","得標","契約"],
    }
    return next((k for k,ws in cats.items() if any(w in subject for w in ws)),"OTHER")

def load_history(path):
    out={}
    for p in sorted(Path(path).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if not ds:continue
            d=datetime.fromisoformat(ds).date()
            by[d].append(b)
        for d in by:by[d].sort(key=lambda z:z["date"])
        out[sym]=by
    return out

def action_day(event_date,event_time,days):
    ds=sorted(days)
    digits=re.sub(r"\D","",event_time or "")
    try: hhmm=int(digits[:4]) if len(digits)>=3 else 9999
    except: hhmm=9999
    if event_date in days and hhmm<=830:return event_date
    return next((d for d in ds if d>event_date),None)

def day_returns(bars):
    if not bars:return None
    op=fnum(bars[0].get("open"))
    if not op or op>100:return None
    r={"entry_open":op}
    for name,idx in HORIZONS.items():
        if len(bars)>idx:
            px=fnum(bars[idx].get("close"))
            if px is not None:r[name]=(px/op-1)*100
    cl=fnum(bars[-1].get("close"))
    if cl is not None:r["close"]=(cl/op-1)*100
    return r

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(x for x in vals if x>0); gl=-sum(x for x in vals if x<0)
    return {"n":len(vals),"win_rate":sum(x>0 for x in vals)/len(vals),
            "expectancy_pct":statistics.mean(vals),"median_pct":statistics.median(vals),
            "pf":gp/gl if gl>0 else None}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--start",default="2023-05-23")
    ap.add_argument("--end",default="2026-10-22")
    ap.add_argument("--out",default="research_output_catalyst_oos")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mani=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    keep={str(x["symbol"]) for x in mani["sample"]}
    hist=load_history(args.history_dir)
    start=datetime.fromisoformat(args.start).date(); end=datetime.fromisoformat(args.end).date()

    sess=requests.Session(); events=[]; errors=[]
    for i,sym in enumerate(sorted(keep),1):
        for yy in range(start.year,end.year+1):
            try:
                for e in parse_company_year(fetch_company_year(sess,sym,yy-1911),sym):
                    d=datetime.fromisoformat(e["announce_date"]).date()
                    if start<=d<=end: events.append({**e,"category":category(e["subject"])})
            except Exception as e:
                errors.append({"symbol":sym,"year":yy,"error":str(e)})
            time.sleep(.20)
        if i%10==0:print(f"fetched {i}/{len(keep)} symbols events={len(events)} errors={len(errors)}",flush=True)

    # Collapse multiple announcements to one symbol/action-day to avoid overweighting announcement bursts.
    grouped={}
    for e in events:
        by=hist.get(e["symbol"])
        if not by:continue
        ed=datetime.fromisoformat(e["announce_date"]).date()
        ad=action_day(ed,e.get("announce_time",""),set(by))
        if ad is None:continue
        key=(e["symbol"],ad)
        g=grouped.setdefault(key,{"symbol":e["symbol"],"action_date":str(ad),"categories":set(),"event_count":0})
        g["categories"].add(e["category"]);g["event_count"]+=1

    rows=[]
    for (sym,ad),g in grouped.items():
        by=hist.get(sym,{})
        d=datetime.fromisoformat(str(ad)).date()
        rr=day_returns(by.get(d,[]))
        if not rr:continue
        rows.append({**g,"categories":";".join(sorted(g["categories"])),**rr})

    splits={"train":[],"valid":[],"test":[]}
    for r in rows:
        y=int(r["action_date"][:4])
        if y<=2024:splits["train"].append(r)
        elif y==2025:splits["valid"].append(r)
        elif y==2026:splits["test"].append(r)

    signals=["ALL_EVENT","EARNINGS","REVENUE","GUIDANCE","CORPORATE_ACTION","INVESTOR_EVENT","CONTRACT_ORDER","OTHER"]
    horizons=list(HORIZONS)+["close"]
    def flag(r,sig):
        if sig=="ALL_EVENT":return True
        return sig in set(r["categories"].split(";"))

    grid={}
    for sig in signals:
        grid[sig]={}
        for h in horizons:
            grid[sig][h]={}
            for c in COSTS:
                ck=f"{c:.2f}"
                grid[sig][h][ck]={}
                for sp,arr in splits.items():
                    vals=[r[h]-c for r in arr if flag(r,sig) and h in r]
                    grid[sig][h][ck][sp]=metrics(vals)

    candidates=[]
    for sig in signals:
        for h in horizons:
            m=grid[sig][h]["0.20"]["train"]
            if m.get("n",0)>=100:
                candidates.append((m.get("expectancy_pct",-999),m.get("pf") or 0,m.get("n",0),sig,h))
    candidates.sort(reverse=True)
    selected={"signal":None,"horizon":None}
    if candidates:
        _,_,_,sig,h=candidates[0];selected={"signal":sig,"horizon":h}

    promo=False;reasons=[]
    if selected["signal"]:
        sig,h=selected["signal"],selected["horizon"]
        vm=grid[sig][h]["0.20"]["valid"];tm=grid[sig][h]["0.20"]["test"]
        promo=(vm.get("n",0)>=100 and tm.get("n",0)>=100 and
               (vm.get("expectancy_pct") or -999)>0 and (tm.get("expectancy_pct") or -999)>0 and
               (vm.get("pf") or 0)>1.05 and (tm.get("pf") or 0)>1.05)
        if not promo:reasons.append("Training-selected catalyst signal failed 2025+2026 promotion gate at 0.20% cost.")

    report={
      "method":"MOPS material-information standalone lagged event OOS",
      "event_timing_rule":"same-day only if announcement <=08:30; otherwise next trading day",
      "rows":len(rows),"events_raw":len(events),"errors":errors[:50],
      "split_counts":{k:len(v) for k,v in splits.items()},
      "costs_pct":COSTS,"selection_rule":"training only at 0.20%, n>=100",
      "promotion_rule":"2025 and 2026 each n>=100, expectancy>0, PF>1.05 at 0.20%",
      "selected":selected,"promotion_pass":promo,"reasons":reasons,"grid":grid,
      "limitations":["Current-universe sample has survivorship bias.",
                     "Event category is keyword-based and descriptive, not sentiment classification.",
                     "No event direction/sentiment is inferred.",
                     "Historical spread/limit-up state unavailable in this dataset."]
    }
    (out/"catalyst_oos_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if rows:
        fields=sorted({k for r in rows for k in r})
        with (out/"catalyst_event_rows.csv").open("w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    lines=["# Sky Catalyst Standalone OOS",f"- Raw events: {len(events)}",f"- Event-days: {len(rows)}",
           f"- Split counts: {report['split_counts']}",f"- Selected: {selected}",f"- Promotion pass: **{promo}**"]
    if selected["signal"]:
        sig,h=selected["signal"],selected["horizon"]
        lines+=["","## Selected @0.20%"]
        for sp in ("train","valid","test"):
            m=grid[sig][h]["0.20"][sp]
            lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
    (out/"catalyst_oos_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
