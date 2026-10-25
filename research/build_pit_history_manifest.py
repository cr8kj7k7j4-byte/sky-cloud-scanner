from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def _d(x):
    return date.fromisoformat(str(x)[:10])


def build_manifest(intervals, *, from_date: str, to_date: str):
    start=_d(from_date); end=_d(to_date)
    symbols={}
    for row in intervals or []:
        a=_d(row["listed_from"])
        b=_d(row["listed_to"]) if row.get("listed_to") else date.max
        if b < start or a > end:
            continue
        key=(str(row["exchange"]),str(row["symbol"]))
        prev=symbols.get(key)
        item={
            "symbol":str(row["symbol"]),
            "exchange":str(row["exchange"]),
            "name":str(row.get("name") or ""),
            "history_required_from":max(a,start).isoformat(),
            "history_required_to":min(b,end).isoformat(),
            "membership_source":row.get("source"),
            "membership_source_as_of":row.get("source_as_of"),
        }
        if prev is None:
            symbols[key]=item
        else:
            prev["history_required_from"]=min(prev["history_required_from"],item["history_required_from"])
            prev["history_required_to"]=max(prev["history_required_to"],item["history_required_to"])
            if item["name"]: prev["name"]=item["name"]

    sample=sorted(symbols.values(),key=lambda x:(x["exchange"],x["symbol"]))
    return {
        "schema_version":"PIT_HISTORY_MANIFEST_V1_0",
        "method":"union of governed PIT membership intervals overlapping requested window",
        "survivorship_bias_warning":None,
        "from":from_date,"to":to_date,
        "symbol_count":len(sample),
        "sample":sample,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pit-universe",required=True)
    ap.add_argument("--from-date",required=True)
    ap.add_argument("--to-date",required=True)
    ap.add_argument("--out",default="research_data/pit_history_manifest.json")
    args=ap.parse_args()
    obj=json.loads(Path(args.pit_universe).read_text(encoding="utf-8"))
    intervals=obj if isinstance(obj,list) else obj.get("intervals",[])
    manifest=build_manifest(intervals,from_date=args.from_date,to_date=args.to_date)
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in manifest.items() if k!="sample"},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
