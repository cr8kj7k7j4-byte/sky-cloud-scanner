from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from research.audit_residual_return_labels import (
    FEATURES,
    HORIZONS,
    build_rows,
    load_daily,
    spearman,
)

COSTS=[0.45,0.65]
TOPNS=[3,5,10]


def metrics(vals):
    if not vals:
        return {"n":0}
    gp=sum(v for v in vals if v>0)
    gl=-sum(v for v in vals if v<0)
    equity=1.0
    peak=1.0
    max_dd=0.0
    for v in vals:
        equity*=1.0+v/100.0
        peak=max(peak,equity)
        if peak>0:
            max_dd=min(max_dd,equity/peak-1.0)
    return {
        "n":len(vals),
        "expectancy_pct":statistics.mean(vals),
        "median_pct":statistics.median(vals),
        "pf":gp/gl if gl>0 else None,
        "win_rate":sum(v>0 for v in vals)/len(vals),
        "max_drawdown_pct":max_dd*100.0,
        "total_return_pct":(equity-1.0)*100.0,
    }


def percentile_map(arr,feature,direction):
    valid=[r for r in arr if r.get(feature) is not None]
    ordered=sorted(valid,key=lambda r:r[feature])
    n=len(ordered)
    out={}
    if n<=1:
        return out
    for rank,row in enumerate(ordered):
        pct=rank/(n-1)
        if direction<0:
            pct=1.0-pct
        out[id(row)]=pct
    return out


def fit_train_directions(train,horizon):
    target=f"market_resid_{horizon}d"
    selected=[]
    for feature in FEATURES:
        rows=[r for r in train if r.get(feature) is not None and r.get(target) is not None]
        ic=spearman([r[feature] for r in rows],[r[target] for r in rows])
        if ic is not None and abs(ic)>=0.02:
            selected.append({
                "feature":feature,
                "direction":1 if ic>0 else -1,
                "train_rank_ic":ic,
            })
    return selected


def score_rows(rows,selected):
    bydate=defaultdict(list)
    for r in rows:
        bydate[r["date"]].append(r)

    scored=[]
    for date,arr in bydate.items():
        maps={
            x["feature"]:percentile_map(arr,x["feature"],x["direction"])
            for x in selected
        }
        for r in arr:
            vals=[]
            for x in selected:
                v=maps[x["feature"]].get(id(r))
                if v is not None:
                    vals.append(v)
            if len(vals)!=len(selected) or not vals:
                continue
            rr=dict(r)
            rr["vnext_score"]=statistics.mean(vals)
            scored.append(rr)
    return scored


def select_daily(rows,topn):
    bydate=defaultdict(list)
    for r in rows:
        bydate[r["date"]].append(r)
    selected=[]
    for date,arr in bydate.items():
        ranked=sorted(
            arr,
            key=lambda r:(r["vnext_score"],r["symbol"]),
            reverse=True,
        )
        for rank,row in enumerate(ranked[:topn],1):
            x=dict(row)
            x["selection_rank"]=rank
            selected.append(x)
    return selected


def evaluate_selection(rows,horizon,cost):
    target=f"market_resid_{horizon}d"
    bydate=defaultdict(list)
    symbols=Counter()
    for r in rows:
        if r.get(target) is None:
            continue
        bydate[r["date"]].append(r)
        symbols[r["symbol"]]+=1

    daily=[]
    position_returns=[]
    for date,arr in sorted(bydate.items()):
        vals=[r[target]-cost for r in arr]
        if not vals:
            continue
        daily.append(statistics.mean(vals))
        position_returns.extend(vals)

    total_positions=sum(symbols.values())
    top_symbol_share=(
        max(symbols.values())/total_positions if total_positions else 0.0
    )
    return {
        "daily_portfolio":metrics(daily),
        "position_level":metrics(position_returns),
        "days":len(daily),
        "positions":total_positions,
        "unique_symbols":len(symbols),
        "top_symbol_share":top_symbol_share,
        "top_symbols":symbols.most_common(10),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--history-dir",required=True)
    ap.add_argument("--out",default="research_output_residual_spread")
    args=ap.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)

    rows=build_rows(load_daily(args.history_dir))
    splits={
        "train":[r for r in rows if int(r["date"][:4])<=2024],
        "validation":[r for r in rows if int(r["date"][:4])==2025],
        "research_test":[r for r in rows if int(r["date"][:4])==2026],
    }

    report={
        "method":"VNext Residual / Market-Neutral Cross-sectional Ranking Baseline v1",
        "preregistration":"research/VNEXT_RESIDUAL_RANKING_PREREGISTRATION.md",
        "horizons":HORIZONS,
        "features":FEATURES,
        "topns":TOPNS,
        "costs_pct":COSTS,
        "split_counts":{k:len(v) for k,v in splits.items()},
        "horizons_results":{},
        "production_eligible":False,
        "fresh_oos":False,
        "promotion_allowed":False,
        "limitations":[
            "2026 is Research Test, not fresh untouched OOS.",
            "Historical universe may still contain survivorship bias until PIT coverage is complete.",
            "Industry residual is disabled until PIT sector mapping is verified.",
            "Capacity cannot be declared fully passed without point-in-time liquidity/capacity evidence.",
        ],
    }

    for h in HORIZONS:
        selected=fit_train_directions(splits["train"],h)
        hres={
            "train_selected_features":selected,
            "variants":{},
        }
        for sp,arr in splits.items():
            scored=score_rows(arr,selected) if selected else []
            hres.setdefault("scored_rows",{})[sp]=len(scored)
            for topn in TOPNS:
                chosen=select_daily(scored,topn)
                key=f"TOP{topn}"
                hres["variants"].setdefault(key,{})
                for cost in COSTS:
                    ck=f"{cost:.2f}"
                    hres["variants"][key].setdefault(ck,{})
                    hres["variants"][key][ck][sp]=evaluate_selection(
                        chosen,h,cost
                    )
        report["horizons_results"][str(h)]=hres

    # No result-based winner selection in v1. All preregistered Top-N variants
    # are reported side by side. Promotion remains impossible without fresh OOS.
    (out/"vnext_residual_ranking_baseline.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )

    lines=[
        "# Sky VNext Residual Ranking Baseline v1",
        f"- Split counts: {report['split_counts']}",
        "- Costs: 0.45% primary / 0.65% stress",
        "- 2026: Research Test, not fresh OOS",
        "- Winner selection: disabled in baseline v1",
        "- Production eligible: False",
    ]
    for h in HORIZONS:
        hr=report["horizons_results"][str(h)]
        feats=hr["train_selected_features"]
        lines.append(f"\n## {h}D")
        lines.append(
            "- Train-selected features: "
            + (", ".join(
                f"{x['feature']}({x['direction']:+d})" for x in feats
            ) if feats else "None")
        )
        for topn in TOPNS:
            v=hr["variants"][f"TOP{topn}"]["0.45"]
            lines.append(f"### Top{topn} @0.45%")
            for sp in ("train","validation","research_test"):
                m=v[sp]["daily_portfolio"]
                conc=v[sp]["top_symbol_share"]
                lines.append(
                    f"- {sp}: days={v[sp]['days']} "
                    f"EV={m.get('expectancy_pct')} PF={m.get('pf')} "
                    f"MDD={m.get('max_drawdown_pct')} "
                    f"top_symbol_share={conc:.4f}"
                )

    (out/"vnext_residual_ranking_baseline.md").write_text(
        "\n".join(lines),encoding="utf-8"
    )
    print("\n".join(lines))


if __name__=="__main__":
    main()
