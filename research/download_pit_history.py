from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from research.download_expanded import get_hist


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--out",default="research_data/pit_history")
    args=ap.parse_args()

    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    sample=list(manifest.get("sample") or [])
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    summary=[]

    for i,item in enumerate(sample,1):
        symbol=str(item["symbol"])
        start=date.fromisoformat(item["history_required_from"])
        end=date.fromisoformat(item["history_required_to"])
        try:
            data=get_hist(symbol,start,end)
            payload={
                **item,
                "timeframe":"5",
                "from":start.isoformat(),
                "to":end.isoformat(),
                "data":data,
            }
            (out/f"{symbol}_5.json").write_text(
                json.dumps(payload,ensure_ascii=False),encoding="utf-8"
            )
            summary.append({
                "symbol":symbol,"exchange":item.get("exchange"),
                "ok":True,"bars":len(data),
                "from":start.isoformat(),"to":end.isoformat(),
            })
            print(f"[{i}/{len(sample)}] {symbol}: {len(data)} bars")
        except Exception as exc:
            summary.append({
                "symbol":symbol,"exchange":item.get("exchange"),
                "ok":False,"bars":0,
                "from":start.isoformat(),"to":end.isoformat(),
                "error":f"{type(exc).__name__}: {exc}",
            })
            print(f"[{i}/{len(sample)}] {symbol}: ERROR {type(exc).__name__}: {exc}")

    p=Path(args.manifest).parent/"pit_history_download_summary.json"
    p.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
