from __future__ import annotations

import json

from research.shard_pit_history_manifest import split_manifest, shard_index
from research.merge_pit_history_shards import merge_shards


def test_sharding_is_deterministic_and_complete():
    m={"sample":[
        {"symbol":"1111","exchange":"TWSE"},
        {"symbol":"2222","exchange":"TWSE"},
        {"symbol":"3333","exchange":"TPEx"},
        {"symbol":"4444","exchange":"TPEx"},
    ]}
    a=split_manifest(m,4)
    b=split_manifest(m,4)
    assert a==b
    symbols=[x["symbol"] for shard in a for x in shard["sample"]]
    assert sorted(symbols)==["1111","2222","3333","4444"]
    assert len(symbols)==len(set(symbols))
    for shard in a:
        for item in shard["sample"]:
            assert shard_index(item["symbol"],4)==shard["shard_index"]


def test_merge_rejects_conflicting_duplicate_symbol(tmp_path):
    r1=tmp_path/"s1";r2=tmp_path/"s2";r1.mkdir();r2.mkdir()
    (r1/"1111_5.json").write_text(json.dumps({"symbol":"1111","data":[1]}),encoding="utf-8")
    (r2/"1111_5.json").write_text(json.dumps({"symbol":"1111","data":[2]}),encoding="utf-8")
    try:
        merge_shards([str(r1),str(r2)],str(tmp_path/"out"))
        assert False, "expected conflict"
    except ValueError as exc:
        assert "conflicting duplicate" in str(exc)


def test_merge_accepts_unique_shards_and_records_checksums(tmp_path):
    roots=[]
    for i,sym in enumerate(("1111","2222")):
        r=tmp_path/f"s{i}";r.mkdir();roots.append(str(r))
        (r/f"{sym}_5.json").write_text(
            json.dumps({"symbol":sym,"data":[{"date":"2026-01-01T09:00:00+08:00"}]}),
            encoding="utf-8",
        )
        (r/"pit_history_download_summary.json").write_text(
            json.dumps([{"symbol":sym,"ok":True,"bars":1}]),encoding="utf-8"
        )
    report=merge_shards(roots,str(tmp_path/"out"))
    assert report["status"]=="PASS"
    assert report["unique_symbols"]==2
    assert len(report["source_files"])==2
