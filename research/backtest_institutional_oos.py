from __future__ import annotations
import argparse, csv, json, math, statistics, tarfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

COSTS=[0.00,0.10,0.20,0.25,0.35]
HORIZONS={"30m":5,"60m":11,"120m":23}
MIN_PREV_TURNOVER=20_000_000.0

def fnum(x):
    try:
        if x in (None,""): return None
        return float(str(x).replace(",",""))
    except Exception:
        return None

def quantile(vals,q):
    xs=sorted(v for v in vals if v is not None and math.isfinite(v))
    if not xs: return None
    pos=(len(xs)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return xs[lo]
    w=pos-lo
    return xs[lo]*(1-w)+xs[hi]*w

def pf(vals):
    gp=sum(v for v in vals if v>0)
    gl=-sum(v for v in vals if v<0)
    return gp/gl if gl>0 else None

def metrics(vals):
    if not vals: return {"n":0}
    return {
        "n":len(vals),
        "win_rate":sum(v>0 for v in vals)/len(vals),
        "expectancy_pct":statistics.mean(vals),
        "median_pct":statistics.median(vals),
        "pf":pf(vals),
    }

def load_history(history_dir):
    per_symbol={}
    for p in sorted(Path(history_dir).glob("*_5.json")):
        obj=json.loads(p.read_text(encoding="utf-8"))
        ex=obj.get("exchange")
        sym=str(obj["symbol"])
        days=defaultdict(list)
        for b in obj.get("data",[]):
            ds=str(b.get("date",""))
            if not ds: continue
            d=datetime.fromisoformat(ds).date().isoformat()
            days[d].append(b)
        daily={}
        for d,bars in days.items():
            bars.sort(key=lambda b:b["date"])
            if not bars: continue
            op=fnum(bars[0].get("open")); cl=fnum(bars[-1].get("close"))
            if op is None or cl is None: continue
            turnover=0.0
            for b in bars:
                v=fnum(b.get("volume")); px=fnum(b.get("average"))
                if px is None: px=fnum(b.get("close"))
                if v is not None and px is not None:
                    turnover += v*1000.0*px
            outcomes={}
            for name,idx in HORIZONS.items():
                if len(bars)>idx:
                    x=fnum(bars[idx].get("close"))
                    if x is not None: outcomes[name]=(x/op-1)*100
            daily[d]={
                "open":op,"close":cl,"turnover":turnover,"bars":len(bars),
                **outcomes
            }
        ds=sorted(daily)
        for i,d in enumerate(ds):
            daily[d]["prev_date"]=ds[i-1] if i>0 else None
            if i>0:
                pc=daily[ds[i-1]]["close"]
                daily[d]["gap_pct"]=(daily[d]["open"]/pc-1)*100 if pc else None
        per_symbol[(sym,ex)]=daily
    return per_symbol

def load_inst(path):
    inst=defaultdict(dict)
    with Path(path).open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            key=(str(r["symbol"]),r["exchange"])
            d=r["date"]
            inst[key][d]={
                "foreign":fnum(r.get("foreign_net")),
                "trust":fnum(r.get("trust_net")),
                "dealer":fnum(r.get("dealer_net")),
                "total":fnum(r.get("total_inst_net")),
            }
    return inst

def build_rows(history,inst):
    rows=[]
    diag={"history_keys":len(history),"inst_keys":len(inst),"exact_key_overlap":len(set(history)&set(inst)),"symbol_overlap":len({k[0] for k in history}&{k[0] for k in inst}),"candidate_days":0,"has_prev_inst":0,"pass_turnover":0,"pass_price":0}
    for key,daily in history.items():
        sym,ex=key
        ids=inst.get(key,{})
        dates=sorted(daily)
        for i,d in enumerate(dates):
            if i<1: continue
            diag["candidate_days"]+=1
            cur=daily[d]
            pdate=dates[i-1]
            prev=daily[pdate]
            flow1=ids.get(pdate)
            if not flow1: continue
            diag["has_prev_inst"]+=1
            if prev["turnover"] < MIN_PREV_TURNOVER: continue
            diag["pass_turnover"]+=1
            if cur["open"]>100: continue
            diag["pass_price"]+=1
            def ratio(field, lookback):
                numer=0.0; denom=0.0; count=0
                for j in range(i-1,max(-1,i-1-lookback),-1):
                    dd=dates[j]
                    fl=ids.get(dd)
                    ddaily=daily[dd]
                    if not fl or fl.get(field) is None or ddaily["turnover"]<=0:
                        continue
                    numer += fl[field]*ddaily["close"]
                    denom += ddaily["turnover"]
                    count += 1
                return (numer/denom if denom>0 else None),count
            f1,_=ratio("foreign",1); t1,_=ratio("trust",1); d1,_=ratio("dealer",1); tot1,_=ratio("total",1)
            tot3,c3=ratio("total",3); tot5,c5=ratio("total",5)
            last5=[]
            ft_pos=False; all3_pos=False
            for j in range(i-1,max(-1,i-6),-1):
                dd=dates[j]; fl=ids.get(dd)
                if fl and fl.get("total") is not None:
                    last5.append(fl["total"]>0)
            if flow1.get("foreign") is not None and flow1.get("trust") is not None:
                ft_pos=flow1["foreign"]>0 and flow1["trust"]>0
            if all(flow1.get(k) is not None for k in ("foreign","trust","dealer")):
                all3_pos=flow1["foreign"]>0 and flow1["trust"]>0 and flow1["dealer"]>0
            row={
                "symbol":sym,"exchange":ex,"date":d,"signal_date":pdate,
                "entry_open":cur["open"],"prev_turnover":prev["turnover"],
                "foreign_flow_turnover_1d":f1,
                "trust_flow_turnover_1d":t1,
                "dealer_flow_turnover_1d":d1,
                "total_flow_turnover_1d":tot1,
                "total_flow_turnover_3d":tot3 if c3>=2 else None,
                "total_flow_turnover_5d":tot5 if c5>=3 else None,
                "positive_total_days_5":sum(last5),
                "flow_days_5":len(last5),
                "concord_ft_pos":ft_pos,
                "concord_all3_pos":all3_pos,
                "gap_pct":cur.get("gap_pct"),
            }
            for h in HORIZONS:
                if h in cur: row[h]=cur[h]
            rows.append(row)
    return rows,diag

def split(rows):
    out={"train":[],"valid":[],"test":[]}
    for r in rows:
        y=int(r["date"][:4])
        if y<=2024: out["train"].append(r)
        elif y==2025: out["valid"].append(r)
        elif y==2026: out["test"].append(r)
    return out

def make_thresholds(train):
    feats=[
        "foreign_flow_turnover_1d","trust_flow_turnover_1d",
        "total_flow_turnover_1d","total_flow_turnover_3d","total_flow_turnover_5d"
    ]
    return {f:quantile([r.get(f) for r in train],0.70) for f in feats}

def flags(r,thr):
    def geq(feature):
        v=r.get(feature); t=thr.get(feature)
        return v is not None and t is not None and v>=t
    return {
        "FOREIGN_1D_Q70": geq("foreign_flow_turnover_1d"),
        "TRUST_1D_Q70": geq("trust_flow_turnover_1d"),
        "TOTAL_1D_Q70": geq("total_flow_turnover_1d"),
        "TOTAL_3D_Q70": geq("total_flow_turnover_3d"),
        "TOTAL_5D_Q70": geq("total_flow_turnover_5d"),
        "PERSIST_TOTAL_4OF5": r.get("flow_days_5",0)>=4 and r.get("positive_total_days_5",0)>=4,
        "CONCORD_FT_POS": bool(r.get("concord_ft_pos")),
        "CONCORD_ALL3_POS": bool(r.get("concord_all3_pos")),
    }

def eval_signal(rows,signal,h,cost,thr):
    vals=[]
    for r in rows:
        if flags(r,thr).get(signal) and h in r:
            vals.append(r[h]-cost)
    return metrics(vals)

def eval_control(rows,signal,h,cost,thr):
    vals=[]
    for r in rows:
        if (not flags(r,thr).get(signal)) and h in r:
            vals.append(r[h]-cost)
    return metrics(vals)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--institutional-csv",required=True)
    ap.add_argument("--out-dir",default="research_output_institutional_oos")
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)

    history=load_history(args.history_dir)
    inst=load_inst(args.institutional_csv)
    rows,diag=build_rows(history,inst)
    splits=split(rows)
    thr=make_thresholds(splits["train"])
    signals=["FOREIGN_1D_Q70","TRUST_1D_Q70","TOTAL_1D_Q70","TOTAL_3D_Q70","TOTAL_5D_Q70",
             "PERSIST_TOTAL_4OF5","CONCORD_FT_POS","CONCORD_ALL3_POS"]

    grid={}
    for sig in signals:
        grid[sig]={}
        for h in HORIZONS:
            grid[sig][h]={}
            for c in COSTS:
                ck=f"{c:.2f}"
                grid[sig][h][ck]={
                    s:eval_signal(splits[s],sig,h,c,thr) for s in ("train","valid","test")
                }

    # Training-only selection at 0.20% cost among tradable horizons.
    candidates=[]
    for sig in signals:
        for h in HORIZONS:
            m=grid[sig][h]["0.20"]["train"]
            if m.get("n",0)>=100:
                candidates.append((m.get("expectancy_pct",-999),m.get("pf") or 0,m.get("n",0),sig,h))
    candidates.sort(reverse=True)
    selected={"signal":None,"horizon":None}
    if candidates:
        _,_,_,ss,hh=candidates[0]
        selected={"signal":ss,"horizon":hh}

    promo=False; reasons=[]
    if selected["signal"]:
        sig,h=selected["signal"],selected["horizon"]
        vm=grid[sig][h]["0.20"]["valid"]; tm=grid[sig][h]["0.20"]["test"]
        promo=(vm.get("n",0)>=100 and tm.get("n",0)>=100 and
               (vm.get("expectancy_pct") or -999)>0 and (tm.get("expectancy_pct") or -999)>0 and
               (vm.get("pf") or 0)>1.05 and (tm.get("pf") or 0)>1.05)
        if not promo:
            reasons.append("Selected training signal did not satisfy both 2025 validation and 2026 OOS promotion gates at 0.20% cost.")

    controls={}
    if selected["signal"]:
        sig,h=selected["signal"],selected["horizon"]
        for c in COSTS:
            ck=f"{c:.2f}"
            controls[ck]={s:eval_control(splits[s],sig,h,c,thr) for s in ("train","valid","test")}

    report={
        "method":"Institutional lag-1 standalone OOS",
        "lookahead_control":"Day t entries use institutional data through t-1 only.",
        "history_symbols":len(history),
        "institutional_symbols":len(inst),
        "eligible_rows":len(rows),
        "join_diagnostics":diag,
        "split_counts":{k:len(v) for k,v in splits.items()},
        "filters":{"entry_price_max":100,"min_previous_day_turnover":MIN_PREV_TURNOVER},
        "training_thresholds_q70":thr,
        "costs_pct":COSTS,
        "horizons":list(HORIZONS),
        "selection_rule":"Choose best training expectancy at 0.20% cost with n>=100; no validation/test information used for selection.",
        "promotion_rule":"2025 validation AND 2026 OOS each n>=100, expectancy>0, PF>1.05 at 0.20% cost.",
        "selected":selected,
        "promotion_pass":promo,
        "reasons":reasons,
        "grid":grid,
        "selected_no_signal_control":controls,
        "limitations":[
            "Current-universe deterministic sample has survivorship bias.",
            "Institutional rows are used only when present; missing rows are not imputed as zero.",
            "Turnover is approximated from 5-minute volume multiplied by average/close price.",
            "Spread and exact limit-up state are unavailable historically in this dataset.",
        ],
    }
    (out/"institutional_oos_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    fields=sorted({k for r in rows for k in r})
    with (out/"institutional_feature_rows.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

    lines=[
        "# Sky Institutional Lag-1 OOS",
        f"- Eligible rows: {len(rows)}",
        f"- Join diagnostics: {diag}",
        f"- Split counts: {report['split_counts']}",
        f"- Selected (training only @0.20%): {selected}",
        f"- Promotion pass: **{promo}**",
    ]
    if selected["signal"]:
        sig,h=selected["signal"],selected["horizon"]
        lines.append("")
        lines.append("## Selected signal @ 0.20%")
        for s in ("train","valid","test"):
            m=grid[sig][h]["0.20"][s]
            lines.append(f"- {s}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
        lines.append("")
        lines.append("## No-signal control @ 0.20%")
        for s in ("train","valid","test"):
            m=controls["0.20"][s]
            lines.append(f"- {s}: n={m.get('n')} exp={m.get('expectancy_pct')} PF={m.get('pf')} win={m.get('win_rate')}")
    lines += ["","## Decision", "- Deploy institutional module only if promotion_pass is true; otherwise keep Sky v0.4 unchanged."]
    (out/"institutional_oos_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":
    main()
