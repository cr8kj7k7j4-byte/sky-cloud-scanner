from __future__ import annotations
import argparse,csv,json,math,statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

COSTS=[0.00,0.10,0.20,0.25,0.35]
ENTRY_INDEX=6  # 09:35 bar open after first 30m (09:00-09:30 inclusive)
EVAL_INDEX={"60m":11,"120m":23,"close":None}

def fnum(x):
    try:
        if x in (None,""): return None
        return float(str(x).replace(",",""))
    except Exception:
        return None

def metrics(vals):
    if not vals:return {"n":0}
    gp=sum(x for x in vals if x>0); gl=-sum(x for x in vals if x<0)
    return {"n":len(vals),
            "win_rate":sum(x>0 for x in vals)/len(vals),
            "expectancy_pct":statistics.mean(vals),
            "median_pct":statistics.median(vals),
            "pf":gp/gl if gl>0 else None}

def load_industry(path):
    j=json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(r["symbol"]):str(r.get("industry_code") or "UNKNOWN") for r in j.get("rows",[])}

def load_taiex(path):
    rows=[]
    with Path(path).open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            c=fnum(r.get("close"))
            if c is not None: rows.append({"date":r["date"],"close":c})
    rows.sort(key=lambda r:r["date"])
    closes=[r["close"] for r in rows]
    out={}
    for i,r in enumerate(rows):
        if i<59:
            regime="UNKNOWN"
        else:
            ma60=sum(closes[i-59:i+1])/60
            ma20=sum(closes[i-19:i+1])/20
            ret20=(closes[i]/closes[i-20]-1) if i>=20 else 0
            if closes[i]>ma60 and ma20>ma60 and ret20>0: regime="BULL"
            elif closes[i]<ma60 and ma20<ma60 and ret20<0: regime="BEAR"
            else: regime="NEUTRAL"
        out[r["date"]]=regime
    return out

def load_history(history_dir,industry):
    symbols={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        o=json.loads(p.read_text(encoding="utf-8"))
        sym=str(o["symbol"]); by=defaultdict(list)
        for b in o.get("data",[]):
            ds=str(b.get("date",""))
            if not ds:continue
            d=datetime.fromisoformat(ds).date().isoformat()
            by[d].append(b)
        daily={}
        for d,bars in by.items():
            bars.sort(key=lambda z:z["date"])
            op=fnum(bars[0].get("open")); cl=fnum(bars[-1].get("close"))
            if op is None or cl is None:continue
            vol=sum((fnum(x.get("volume")) or 0) for x in bars)
            daily[d]={"bars":bars,"open":op,"close":cl,"volume":vol}
        dates=sorted(daily)
        for i,d in enumerate(dates):
            daily[d]["prev_date"]=dates[i-1] if i>0 else None
            if i>0:
                pc=daily[dates[i-1]]["close"]
                daily[d]["prev_ret_pct"]=(daily[d]["open"]/pc-1)*100 if pc else None
                daily[dates[i-1]]["day_ret_pct"]=(daily[dates[i-1]]["close"]/daily[dates[i-1]]["open"]-1)*100 if daily[dates[i-1]]["open"] else None
        symbols[sym]={"industry":industry.get(sym,"UNKNOWN"),"daily":daily}
    return symbols

def build_sector_prev(symbols):
    groups=defaultdict(list)
    for sym,obj in symbols.items():
        sec=obj["industry"]
        for d,rec in obj["daily"].items():
            if rec.get("day_ret_pct") is not None:
                groups[(d,sec)].append(rec["day_ret_pct"])
    return {(d,s):statistics.mean(v) for (d,s),v in groups.items() if v}

def load_events(path):
    rows=[]
    with Path(path).open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def first30_features(bars):
    if len(bars)<=ENTRY_INDEX:return None
    xs=bars[:6]
    op=fnum(xs[0].get("open")); c=fnum(xs[-1].get("close"))
    if op is None or c is None:return None
    vols=[fnum(x.get("volume")) or 0 for x in xs]
    avgs=[]
    for x in xs:
        a=fnum(x.get("average"))
        if a is None:a=fnum(x.get("close"))
        avgs.append(a)
    den=sum(vols)
    vwap=sum(v*a for v,a in zip(vols,avgs) if a is not None)/den if den>0 else None
    ret=(c/op-1)*100 if op else None
    dist=(c/vwap-1)*100 if vwap else None
    hi=max(fnum(x.get("high")) for x in xs if fnum(x.get("high")) is not None)
    lo=min(fnum(x.get("low")) for x in xs if fnum(x.get("low")) is not None)
    pos=(c-lo)/(hi-lo) if hi>lo else None
    anti=(ret is not None and ret<4.0 and (dist is None or dist<2.0) and not (ret>=3.0 and pos is not None and pos>=0.95))
    confirm=(ret is not None and ret>0 and vwap is not None and c>=vwap)
    return {"ret30":ret,"vwap":vwap,"vwap_dist":dist,"range_pos":pos,"confirm":confirm,"anti":anti}

def outcome_from_entry(bars):
    if len(bars)<=ENTRY_INDEX:return None
    entry=fnum(bars[ENTRY_INDEX].get("open"))
    if entry is None or entry>100:return None
    out={"entry":entry}
    for name,idx in EVAL_INDEX.items():
        px=fnum(bars[-1].get("close")) if idx is None else (fnum(bars[idx].get("close")) if len(bars)>idx else None)
        if px is not None: out[name]=(px/entry-1)*100
    return out

def flags(row):
    return {
      "EVT_ONLY":True,
      "EVT_NONBEAR":row["market_regime"]!="BEAR",
      "EVT_NONBEAR_SECTOR":row["market_regime"]!="BEAR" and row["sector_prev_ret"]>0,
      "EVT_NONBEAR_SECTOR_RS":row["market_regime"]!="BEAR" and row["sector_prev_ret"]>0 and row["stock_prev_ret"]>row["sector_prev_ret"],
      "FULL_CONFIRM":row["market_regime"]!="BEAR" and row["sector_prev_ret"]>0 and row["stock_prev_ret"]>row["sector_prev_ret"] and row["price_confirm"] and row["anti_chase"],
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--event-csv",required=True)
    ap.add_argument("--industry-json",required=True)
    ap.add_argument("--taiex-csv",required=True)
    ap.add_argument("--out",default="research_output_event_stack_oos")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    industry=load_industry(args.industry_json)
    taiex=load_taiex(args.taiex_csv)
    symbols=load_history(args.history_dir,industry)
    sector=build_sector_prev(symbols)
    events=load_events(args.event_csv)

    rows=[]; diag={"event_rows":len(events),"symbol_match":0,"day_match":0,"feature_ready":0}
    for e in events:
        sym=str(e["symbol"]); ad=e["action_date"]
        obj=symbols.get(sym)
        if not obj:continue
        diag["symbol_match"]+=1
        rec=obj["daily"].get(ad)
        if not rec:continue
        diag["day_match"]+=1
        pd=rec.get("prev_date")
        if not pd:continue
        prev=obj["daily"].get(pd,{})
        stock_prev=prev.get("day_ret_pct")
        sec_prev=sector.get((pd,obj["industry"]))
        market=taiex.get(pd,"UNKNOWN")
        p30=first30_features(rec["bars"])
        oc=outcome_from_entry(rec["bars"])
        if stock_prev is None or sec_prev is None or p30 is None or oc is None:continue
        diag["feature_ready"]+=1
        rows.append({
          "symbol":sym,"action_date":ad,"signal_prev_date":pd,"categories":e.get("categories",""),
          "market_regime":market,"industry":obj["industry"],
          "stock_prev_ret":stock_prev,"sector_prev_ret":sec_prev,
          "price_confirm":p30["confirm"],"anti_chase":p30["anti"],
          "ret30":p30["ret30"],"vwap_dist":p30["vwap_dist"],"entry":oc["entry"],
          **{k:v for k,v in oc.items() if k!="entry"}
        })

    splits={"train":[],"valid":[],"test":[]}
    for r in rows:
        y=int(r["action_date"][:4])
        if y<=2024:splits["train"].append(r)
        elif y==2025:splits["valid"].append(r)
        elif y==2026:splits["test"].append(r)

    variants=["EVT_ONLY","EVT_NONBEAR","EVT_NONBEAR_SECTOR","EVT_NONBEAR_SECTOR_RS","FULL_CONFIRM"]
    horizons=list(EVAL_INDEX)
    grid={}
    for v in variants:
        grid[v]={}
        for h in horizons:
            grid[v][h]={}
            for c in COSTS:
                ck=f"{c:.2f}";grid[v][h][ck]={}
                for sp,arr in splits.items():
                    vals=[r[h]-c for r in arr if flags(r)[v] and h in r]
                    grid[v][h][ck][sp]=metrics(vals)

    candidates=[]
    for v in variants:
        for h in horizons:
            m=grid[v][h]["0.20"]["train"]
            if m.get("n",0)>=100:
                candidates.append((m.get("expectancy_pct",-999),m.get("pf") or 0,m.get("n",0),v,h))
    candidates.sort(reverse=True)
    selected={"variant":None,"horizon":None}
    if candidates:
        _,_,_,v,h=candidates[0];selected={"variant":v,"horizon":h}

    promo=False;reasons=[]
    if selected["variant"]:
        v,h=selected["variant"],selected["horizon"]
        vm=grid[v][h]["0.20"]["valid"];tm=grid[v][h]["0.20"]["test"]
        promo=(vm.get("n",0)>=100 and tm.get("n",0)>=100 and
               (vm.get("expectancy_pct") or -999)>0 and (tm.get("expectancy_pct") or -999)>0 and
               (vm.get("pf") or 0)>1.05 and (tm.get("pf") or 0)>1.05)
        if not promo:reasons.append("Training-selected event stack failed 2025+2026 promotion gate at 0.20% cost.")

    report={
      "method":"Event evidence stack OOS with prior-day market/sector/RS and action-day 30m confirmation",
      "lookahead_control":"Market, sector and stock RS use prior completed trading day; price confirmation uses first 30m, entry is next 5m bar open.",
      "diagnostics":diag,"eligible_rows":len(rows),"split_counts":{k:len(v) for k,v in splits.items()},
      "variants":variants,"costs_pct":COSTS,
      "selection_rule":"Training only at 0.20%, n>=100; validation/test not used for selection.",
      "promotion_rule":"2025 and 2026 each n>=100, expectancy>0, PF>1.05 at 0.20%.",
      "selected":selected,"promotion_pass":promo,"reasons":reasons,"grid":grid,
      "limitations":["Current-universe sample has survivorship bias.",
                     "Industry classification is current classification applied backward.",
                     "Sector strength is computed within the fixed 100-stock sample, not full-market sector breadth.",
                     "Historical spread and exact limit-up state unavailable."]
    }
    (out/"event_stack_oos_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if rows:
        fields=sorted({k for r in rows for k in r})
        with (out/"event_stack_rows.csv").open("w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    lines=["# Sky Event Evidence Stack OOS",f"- Eligible rows: {len(rows)}",f"- Split counts: {report['split_counts']}",
           f"- Selected: {selected}",f"- Promotion pass: **{promo}**"]
    if selected["variant"]:
        v,h=selected["variant"],selected["horizon"]
        lines+=["","## Selected @0.20%"]
        for sp in ("train","valid","test"):
            m=grid[v][h]["0.20"][sp]
            lines.append(f"- {sp}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
    (out/"event_stack_oos_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
