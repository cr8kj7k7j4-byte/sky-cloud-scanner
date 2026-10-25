from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def shard_index(symbol: str, shard_count: int) -> int:
    digest=hashlib.sha256(str(symbol).encode("utf-8")).hexdigest()
    return int(digest[:16],16)%int(shard_count)


def split_manifest(manifest: dict, shard_count: int) -> list[dict]:
    sample=list(manifest.get("sample") or [])
    shards=[[] for _ in range(int(shard_count))]
    for item in sample:
        shards[shard_index(str(item["symbol"]),shard_count)].append(item)
    out=[]
    for i,rows in enumerate(shards):
        out.append({
            "schema_version":"PIT_HISTORY_SHARD_MANIFEST_V1_0",
            "parent_schema_version":manifest.get("schema_version"),
            "parent_method":manifest.get("method"),
            "from":manifest.get("from"),
            "to":manifest.get("to"),
            "shard_count":int(shard_count),
            "shard_index":i,
            "symbol_count":len(rows),
            "sample":sorted(rows,key=lambda x:(str(x.get("exchange")),str(x.get("symbol")))),
        })
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--shard-count",type=int,default=8)
    ap.add_argument("--out-dir",default="research_data/pit_history_shards")
    args=ap.parse_args()
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    shards=split_manifest(manifest,args.shard_count)
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    index=[]
    for shard in shards:
        p=out/f"manifest_shard_{shard['shard_index']:02d}.json"
        p.write_text(json.dumps(shard,ensure_ascii=False,indent=2),encoding="utf-8")
        index.append({
            "shard_index":shard["shard_index"],
            "symbol_count":shard["symbol_count"],
            "path":str(p),
        })
    (out/"index.json").write_text(
        json.dumps({"shard_count":len(shards),"shards":index},ensure_ascii=False,indent=2),
        encoding="utf-8",
    )
    print(json.dumps(index,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
