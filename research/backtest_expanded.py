
from __future__ import annotations
import argparse, csv, json, statistics
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path

SCAN_TIMES = [time(9,10), time(10,10), time(11,10), time(12,10), time(13,0)]
HORIZONS = [6,12,24]  # 30/60/120m
COSTS = [0.25,0.35,0.45,0.55]

def dt(s): return datetime.fromisoformat(s)

def group_day(data):
    out=defaultdict(list)
    for b in data:
        x={**b,"_dt":dt(b["date"])}
        out[x["_dt"].date()].append(x)
    for d in out: out[d].sort(key=lambda x:x["_dt"])
    return out

def prev_close(by):
    ds=sorted(by); out={}
    for i,d in enumerate(ds):
        out[d]=None if i==0 or not by[ds[i-1]] else float(by[ds[i-1]][-1]["close"])
    return out

def snap(bars, t, pc):
    xs=[b for b in bars if b["_dt"].time()<=t]
    if len(xs)<2 or not pc: return None
    cur,prv=xs[-1],xs[-2]
    close=float(cur["close"]); avg=cur.get("average")
    avg=float(avg) if avg not in (None,"") else None
    hi=max(float(x["high"]) for x in xs); lo=min(float(x["low"]) for x in xs)
    chg=(close/pc-1)*100
    avgdist=(close/avg-1)*100 if avg else None
    pos=(close-lo)/(hi-lo) if hi>lo else None
    anti=[]
    if chg>=8: anti.append("chg>=8")
    if avgdist is not None and avgdist>=4: anti.append("avgdist>=4")
    if chg>=6 and pos is not None and pos>=.92 and avgdist is not None and avgdist>=2.5:
        anti.append("high_extension")
    return {
        "idx":len(xs)-1,"close":close,"change_pct":chg,
        "above_avg":(close>=avg) if avg else None,
        "avg_distance_pct":avgdist,"range_pos":pos,
        "anti_pass":not anti,"anti_reasons":";".join(anti),
    }

def excursion(bars, idx, hb):
    fut=bars[idx+1:min(len(bars),idx+hb+1)]
    if not fut: return None
    e=float(bars[idx]["close"])
    return {
        "ret":(float(fut[-1]["close"])/e-1)*100,
        "mfe":(max(float(x["high"]) for x in fut)/e-1)*100,
        "mae":(min(float(x["low"]) for x in fut)/e-1)*100,
    }

def raw_rows(files):
    rows=[]
    for p in files:
        obj=json.loads(p.read_text(encoding="utf-8"))
        by=group_day(obj["data"]); pc=prev_close(by)
        for d,bars in by.items():
            for t in SCAN_TIMES:
                s=snap(bars,t,pc[d])
                if not s or s["close"]>100: continue
                row={
                    "symbol":obj["symbol"],"exchange":obj.get("exchange"),
                    "date":str(d),"scan_time":t.strftime("%H:%M"),**s
                }
                for hb in HORIZONS:
                    e=excursion(bars,s["idx"],hb)
                    if e:
                        row[f"ret_{hb}"]=e["ret"]; row[f"mfe_{hb}"]=e["mfe"]; row[f"mae_{hb}"]=e["mae"]
                rows.append(row)
    return rows

def add_cross_section(rows):
    groups=defaultdict(list)
    for r in rows:
        groups[(r["date"],r["scan_time"])].append(r)
    for _, arr in groups.items():
        chgs=sorted(r["change_pct"] for r in arr)
        if not chgs: continue
        n=len(chgs)
        med=chgs[n//2] if n%2 else (chgs[n//2-1]+chgs[n//2])/2
        adv=sum(x>0 for x in chgs)/n
        dec=sum(x<0 for x in chgs)/n
        risk_off=(dec>=.60 and med<=-.50)
        for r in arr:
            r["sample_n"]=n
            r["market_median_change"]=med
            r["adv_ratio"]=adv
            r["market_risk_off"]=risk_off
            r["market_rs_pp"]=r["change_pct"]-med
            r["market_rs_pass"]=r["market_rs_pp"]>=0
    return rows

def flags(r):
    base = r["change_pct"]>0 and r["above_avg"] is True
    ac = base and r["anti_pass"]
    rs = ac and r.get("market_rs_pass",False)
    mg = rs and not r.get("market_risk_off",True)
    return {"V04_BASE":base,"V05_AC":ac,"V05_AC_RS":rs,"V05_AC_RS_MG":mg}

def metrics(rows, flag, hb, cost):
    vals=[]; mfes=[]; maes=[]
    for r in rows:
        if flags(r)[flag] and f"ret_{hb}" in r:
            vals.append(r[f"ret_{hb}"]-cost)
            mfes.append(r[f"mfe_{hb}"]); maes.append(r[f"mae_{hb}"])
    if not vals: return {"n":0}
    w=[x for x in vals if x>0]; l=[x for x in vals if x<0]
    gp=sum(w); gl=-sum(l)
    return {
        "n":len(vals),
        "win_rate":sum(x>0 for x in vals)/len(vals),
        "expectancy_net_pct":statistics.mean(vals),
        "median_net_pct":statistics.median(vals),
        "pf_net":gp/gl if gl>0 else None,
        "payoff":statistics.mean(w)/abs(statistics.mean(l)) if w and l else None,
        "avg_mfe_pct":statistics.mean(mfes),
        "avg_mae_pct":statistics.mean(maes),
    }

def yearly(rows, flag, hb, cost):
    out={}
    years=sorted({r["date"][:4] for r in rows})
    for y in years:
        out[y]=metrics([r for r in rows if r["date"].startswith(y)], flag, hb, cost)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",default="research_data/history")
    ap.add_argument("--out",default="research_output_expanded")
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)

    files=sorted(Path(args.data_dir).glob("*_5.json"))
    rows=add_cross_section(raw_rows(files))

    variants=["V04_BASE","V05_AC","V05_AC_RS","V05_AC_RS_MG"]
    report={
        "scope":"Expanded deterministic-sample replay; not full-market validation.",
        "data_files":len(files),
        "rows":len(rows),
        "survivorship_bias_warning":"Current listing universe sampled backward; delisted names absent.",
        "sector_rs_status":"NOT_VALIDATED",
        "variants":{},
    }
    for hb in HORIZONS:
        h=f"{hb*5}m"; report["variants"][h]={}
        for cost in COSTS:
            ck=f"cost_{cost:.2f}pct"; report["variants"][h][ck]={}
            for v in variants:
                report["variants"][h][ck][v]={
                    "all":metrics(rows,v,hb,cost),
                    "by_year":yearly(rows,v,hb,cost),
                }

    # Promotion rule focuses on 60m / 0.45% and cross-year stability.
    base=report["variants"]["60m"]["cost_0.45pct"]["V04_BASE"]["all"]
    cand=report["variants"]["60m"]["cost_0.45pct"]["V05_AC_RS_MG"]["all"]
    byy=report["variants"]["60m"]["cost_0.45pct"]["V05_AC_RS_MG"]["by_year"]

    verdict="INSUFFICIENT"
    reasons=[]
    if cand.get("n",0)>=100:
        positive_years=sum(1 for m in byy.values() if m.get("n",0)>=20 and (m.get("expectancy_net_pct") or 0)>0)
        tested_years=sum(1 for m in byy.values() if m.get("n",0)>=20)
        if (cand.get("expectancy_net_pct") or -999)>0 and (cand.get("pf_net") or 0)>1.0 and tested_years>=2 and positive_years>=max(2,tested_years-1):
            verdict="PASS_FOR_RULE_INTEGRATION_REVIEW"
            reasons.append("60m/0.45% candidate is positive with PF>1 and cross-year support.")
        elif (cand.get("expectancy_net_pct") or -999) > (base.get("expectancy_net_pct") or -999):
            verdict="REVISE"
            reasons.append("Candidate improves baseline but is not robustly positive across periods.")
        else:
            verdict="REJECT_CURRENT_COMBINATION"
            reasons.append("Expanded candidate does not improve baseline economics.")
    else:
        reasons.append("Candidate sample below 100.")

    report["verdict"]=verdict
    report["verdict_reasons"]=reasons
    (out/"expanded_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    # Compact CSV of raw scan snapshots for audit.
    if rows:
        fields=sorted({k for r in rows for k in r})
        with (out/"expanded_rows.csv").open("w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

    lines=[
        "# Sky v0.5 Expanded Backtest",
        f"- Verdict: **{verdict}**",
        f"- Symbols with data: {len(files)}",
        f"- Scan snapshots: {len(rows)}",
        "",
        "## Primary comparison (60m, cost 0.45%)",
    ]
    for v in variants:
        m=report["variants"]["60m"]["cost_0.45pct"][v]["all"]
        lines.append(f"- {v}: n={m.get('n')} exp={m.get('expectancy_net_pct')} PF={m.get('pf_net')} win={m.get('win_rate')}")
    lines += [
        "",
        "## Limits",
        "- Deterministic current-universe sample; survivorship bias remains.",
        "- Sector RS not validated.",
        "- This result alone cannot produce A+ or authorize live deployment.",
    ]
    (out/"expanded_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
