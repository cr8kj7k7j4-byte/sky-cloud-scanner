from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def merge_shards(shard_roots: list[str], out_dir: str) -> dict:
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    hist=out/"history";hist.mkdir(parents=True,exist_ok=True)
    seen={}
    summaries=[]
    duplicate_symbols=[]
    source_files=[]

    for root_s in shard_roots:
        root=Path(root_s)
        summary_path=root/"pit_history_download_summary.json"
        if summary_path.exists():
            summaries.extend(json.loads(summary_path.read_text(encoding="utf-8")))
        for p in sorted(root.rglob("*_5.json")):
            symbol=p.name.split("_")[0]
            digest=sha256(p)
            source_files.append({
                "symbol":symbol,"source":str(p),"sha256":digest,"bytes":p.stat().st_size,
            })
            if symbol in seen:
                duplicate_symbols.append(symbol)
                if seen[symbol]!=digest:
                    raise ValueError(f"conflicting duplicate history file for {symbol}")
                continue
            seen[symbol]=digest
            shutil.copy2(p,hist/p.name)

    summary_by_symbol={}
    for row in summaries:
        symbol=str(row.get("symbol") or "")
        if not symbol:
            continue
        prev=summary_by_symbol.get(symbol)
        if prev is not None and prev!=row:
            raise ValueError(f"conflicting download summaries for {symbol}")
        summary_by_symbol[symbol]=row

    merged_summary=[summary_by_symbol[k] for k in sorted(summary_by_symbol)]
    (out/"pit_history_download_summary.json").write_text(
        json.dumps(merged_summary,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    manifest={
        "schema_version":"PIT_HISTORY_SHARD_MERGE_V1_0",
        "shard_roots":shard_roots,
        "unique_symbols":len(seen),
        "duplicate_symbols":sorted(set(duplicate_symbols)),
        "history_files":len(seen),
        "summary_rows":len(merged_summary),
        "source_files":source_files,
        "status":"PASS",
    }
    (out/"merge_manifest.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    return manifest


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shard-root",action="append",required=True)
    ap.add_argument("--out-dir",default="research_output/pit_history_merged")
    args=ap.parse_args()
    report=merge_shards(args.shard_root,args.out_dir)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
