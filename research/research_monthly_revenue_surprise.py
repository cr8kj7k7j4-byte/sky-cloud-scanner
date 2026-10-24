from __future__ import annotations
import argparse, io, json, math, re, statistics, urllib.request
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import pandas as pd

HORIZONS=[5,10,20]
COSTS=[0.20,0.45]
FEATURES=["yoy","mom","yoy_accel","cum_yoy","new_high_12m"]

def fnum(x):
    try:
        if x is None:return None
        s=str(x).strip().replace(",","").replace("%","")
        if s in ("","nan","NaN","None","--","-"):return None
        return float(s)
    except Exception:return None

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(v for v in vals if v>0);gl=-sum(v for v in vals if v<0)
    return {"n":len(vals),"expectancy_pct":statistics.mean(vals),
            "pf":gp/gl if gl>0 else None,
            "win_rate":sum(v>0 for v in vals)/len(vals),
            "median_pct":statistics.median(vals)}

def ranks(vals):
    order=sorted(range(len(vals)),key=lambda i:vals[i]);out=[0.0]*len(vals);i=0
    while i<len(order):
        j=i
        while j+1<len(order) and vals[order[j+1]]==vals[order[i]]:j+=1
        rr=(i+j)/2
        for k in range(i,j+1):out[order[k]]=rr
        i=j+1
    return out

def pearson(x,y):
    if len(x)<3:return None
    mx=statistics.mean(x);my=statistics.mean(y)
    num=sum((a-mx)*(b-my) for a,b in zip(x,y))
    dx=sum((a-mx)**2 for a in x);dy=sum((b-my)**2 for b in y)
    if dx<=0 or dy<=0:return None
    return num/(dx*dy)**0.5

def spearman(x,y):return pearson(ranks(x),ranks(y)) if len(x)>=3 else None

def roc_ym(y,m):return y-1911,m

def next_month(y,m):
    return (y+1,1) if m==12 else (y,m+1)

def fetch_mops_month(y,m,market,foreign):
    ry,rm=roc_ym(y,m)
    kind="sii" if market=="TWSE" else "otc"
    suffix=1 if foreign else 0
    url=f"https://mopsov.twse.com.tw/nas/t21/{kind}/t21sc03_{ry}_{rm}_{suffix}.html"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read()
    # historical MOPS pages are traditionally big5
    text=raw.decode("big5",errors="ignore")
    tables=pd.read_html(io.StringIO(text))
    out=[]
    for t in tables:
        # flatten multiindex headers
        if isinstance(t.columns,pd.MultiIndex):
            t.columns=["".join(str(x) for x in c if str(x)!="nan").strip() for c in t.columns]
        else:t.columns=[str(c).strip() for c in t.columns]
        cols=list(t.columns)
        code_col=next((c for c in cols if "公司代號" in c),None)
        rev_col=next((c for c in cols if "當月營收" in c and "累計" not in c),None)
        prev_col=next((c for c in cols if "上月營收" in c),None)
        ly_col=next((c for c in cols if "去年當月營收" in c),None)
        mom_col=next((c for c in cols if "上月比較" in c and "增減" in c),None)
        yoy_col=next((c for c in cols if "去年同月" in c and "增減" in c),None)
        cum_yoy_col=next((c for c in cols if "前期比較" in c and "增減" in c),None)
        if not code_col or not rev_col:continue
        for _,r in t.iterrows():
            code=str(r.get(code_col,"")).strip()
            code=re.sub(r"\.0$","",code)
            if not re.fullmatch(r"\d{4,6}",code):continue
            rev=fnum(r.get(rev_col))
            if rev is None:continue
            out.append({
                "symbol":code,"year":y,"month":m,"market":market,
                "revenue":rev,
                "prev_revenue":fnum(r.get(prev_col)) if prev_col else None,
                "last_year_revenue":fnum(r.get(ly_col)) if ly_col else None,
                "mom":fnum(r.get(mom_col)) if mom_col else None,
                "yoy":fnum(r.get(yoy_col)) if yoy_col else None,
                "cum_yoy":fnum(r.get(cum_yoy_col)) if cum_yoy_col else None,
                "source_url":url
            })
    return out

def load_price_daily(history_dir):
    bysym={}
    all_dates=set()
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"));sym=str(o["symbol"]);by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if ds:
                d=datetime.fromisoformat(ds).date().isoformat()
                by[d].append(b);all_dates.add(d)
        days=[]
        for d,bars in sorted(by.items()):
            bars.sort(key=lambda x:x["date"])
            op=fnum(bars[0].get("open"));cl=fnum(bars[-1].get("close"))
            if op is None or cl is None:continue
            days.append({"date":d,"open":op,"close":cl})
        bysym[sym]=days
    return bysym,sorted(all_dates)

def first_trading_after_10th(y,m,trading_dates):
    ny,nm=next_month(y,m)
    cutoff=date(ny,nm,10).isoformat()
    for d in trading_dates:
        if d>cutoff:return d
    return None

def enrich_revenue(rows):
    by=defaultdict(list)
    for r in rows:by[r["symbol"]].append(r)
    out=[]
    for sym,arr in by.items():
        arr.sort(key=lambda r:(r["year"],r["month"]))
        rev_hist=[]
        prev_yoy=None
        for r in arr:
            yoy=r.get("yoy");mom=r.get("mom")
            if yoy is None and r.get("last_year_revenue"):
                yoy=(r["revenue"]/r["last_year_revenue"]-1)*100
            if mom is None and r.get("prev_revenue"):
                mom=(r["revenue"]/r["prev_revenue"]-1)*100
            r["yoy"]=yoy;r["mom"]=mom
            r["yoy_accel"]=yoy-prev_yoy if yoy is not None and prev_yoy is not None else None
            hist=rev_hist[-11:]+[r["revenue"]]
            r["new_high_12m"]=1.0 if len(hist)>=12 and r["revenue"]>=max(hist) else 0.0
            rev_hist.append(r["revenue"])
            if yoy is not None:prev_yoy=yoy
            out.append(r)
    return out

def build_events(rev_rows,bysym,trading_dates):
    price_lookup={}
    for sym,days in bysym.items():
        price_lookup[sym]={x["date"]:i for i,x in enumerate(days)}
    events=[]
    for r in rev_rows:
        sym=r["symbol"]
        if sym not in bysym:continue
        kd=first_trading_after_10th(r["year"],r["month"],trading_dates)
        if not kd:continue
        days=bysym[sym]; idx=price_lookup[sym].get(kd)
        if idx is None:continue
        entry_idx=idx
        entry=days[entry_idx]["open"]
        if entry is None or entry>100:continue
        e={**r,"knowledge_date":kd,"entry":entry}
        ok=False
        for h in HORIZONS:
            j=entry_idx+h
            if j<len(days):
                e[f"ret_{h}d"]=(days[j]["close"]/entry-1)*100;ok=True
        if ok:events.append(e)
    return events

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_revenue")
    ap.add_argument("--start", default="2022-12")
    ap.add_argument("--end", default="2026-09")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    sy,sm=map(int,args.start.split("-"));ey,em=map(int,args.end.split("-"))
    months=[];y,m=sy,sm
    while (y,m)<=(ey,em):
        months.append((y,m));y,m=next_month(y,m)

    all_rev=[];failures=[]
    for y,m in months:
        for market in ("TWSE","TPEx"):
            for foreign in (False,True):
                try:all_rev.extend(fetch_mops_month(y,m,market,foreign))
                except Exception as e:failures.append({"year":y,"month":m,"market":market,"foreign":foreign,"error":str(e)})

    # de-duplicate symbol-month, domestic preferred by first seen
    dedup={}
    for r in all_rev:dedup.setdefault((r["symbol"],r["year"],r["month"]),r)
    rev_rows=enrich_revenue(list(dedup.values()))
    bysym,trading_dates=load_price_daily(args.history_dir)
    events=build_events(rev_rows,bysym,trading_dates)

    splits={"train":[e for e in events if int(e["knowledge_date"][:4])<=2024],
            "valid":[e for e in events if int(e["knowledge_date"][:4])==2025],
            "test":[e for e in events if int(e["knowledge_date"][:4])==2026]}

    report={"method":"Monthly Revenue Surprise / Acceleration Research",
            "alignment":"Revenue month becomes usable on first sample trading day strictly after next-month day 10.",
            "features":FEATURES,"horizons":HORIZONS,"costs":COSTS,
            "months":[args.start,args.end],
            "raw_rows":len(all_rev),"dedup_rows":len(rev_rows),"events":len(events),
            "split_counts":{k:len(v) for k,v in splits.items()},
            "failures":failures,"results":{},"stable":[],"production_eligible":False,
            "limitations":["Conservative knowledge-date proxy uses statutory deadline rather than company-level filing timestamp.","Current-universe survivorship bias.","Fixed 100-stock price sample.","2026 is not globally untouched OOS."]}

    for h in HORIZONS:
      target=f"ret_{h}d"
      for f in FEATURES:
        rr={};signs=[];ok=True
        for sp,arr in splits.items():
            a=[e for e in arr if e.get(f) is not None and e.get(target) is not None]
            ic=spearman([e[f] for e in a],[e[target] for e in a]) if len(a)>=30 else None
            rr[sp]={"rank_ic":ic,"n":len(a)}
            if ic is None:ok=False
            else:signs.append(1 if ic>0 else -1)
        stable=ok and len(set(signs))==1 and min(abs(rr[s]["rank_ic"]) for s in ("train","valid","test"))>=0.02
        rr["stable"]=stable
        report["results"][f"{f}_{h}d"]=rr
        if stable:report["stable"].append({"feature":f,"horizon":h,"sign":signs[0]})

    # simple quantile long-only audit for stable pairs using split-local top/bottom deciles only as diagnostics
    report["quantiles"]={}
    for x in report["stable"]:
        f=x["feature"];h=x["horizon"];t=f"ret_{h}d";sign=x["sign"];key=f"{f}_{h}d"
        report["quantiles"][key]={}
        for c in COSTS:
            ck=f"{c:.2f}";report["quantiles"][key][ck]={}
            for sp,arr in splits.items():
                a=[e for e in arr if e.get(f) is not None and e.get(t) is not None]
                a=sorted(a,key=lambda e:e[f]);k=max(1,len(a)//10)
                chosen=a[-k:] if sign>0 else a[:k]
                report["quantiles"][key][ck][sp]=metrics([e[t]-c for e in chosen])

    pd.DataFrame(rev_rows).to_csv(out/"monthly_revenue_history.csv",index=False,encoding="utf-8-sig")
    (out/"monthly_revenue_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky Monthly Revenue Surprise / Acceleration Research",
           f"- Revenue rows: {len(rev_rows)} | events: {len(events)} | failures: {len(failures)}",
           f"- Split counts: {report['split_counts']}",
           f"- Stable pairs: {report['stable']}"]
    for key,q in report["quantiles"].items():
        lines.append(f"\n## {key} @0.45%")
        for sp in ("train","valid","test"):
            lines.append(f"- {sp}: {q['0.45'][sp]}")
    (out/"monthly_revenue_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
