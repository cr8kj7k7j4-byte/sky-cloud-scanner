"""W3A evidence-only probe for historical corporate action event sources.

Never infer absence of corporate actions from empty/failed source responses.
TWSE TWT49U omits some capital reductions, TPEx exDailyQ likewise is not
proof of the complete universe of corporate actions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from src.http_utils import get_json

SOURCES = {
    "TWSE_EXRIGHT_REFERENCE": (
        "https://www.twse.com.tw/exchangeReport/TWT49U",
        {"response":"json", "strDate":"20261023","endDate":"20261104"},
    ),
    "TWSE_EXRIGHT_ALT_START": (
        "https://www.twse.com.tw/exchangeReport/TWT49U",
        {"response":"json", "startDate":"20261023","endDate":"20261104"},
    ),
    "TWSE_EXRIGHT_RWD_STR": (
        "https://www.twse.com.tw/rwd/zh/exRight/TWT49U",
        {"response":"json", "strDate":"20261023","endDate":"20261104"},
    ),
    "TWSE_EXRIGHT_RWD_START": (
        "https://www.twse.com.tw/rwd/zh/exRight/TWT49U",
        {"response":"json", "startDate":"20261023","endDate":"20261104"},
    ),
    "TPEX_EXRIGHT_REFERENCE": (
        "https://www.tpex.org.tw/www/zh-tw/bulletin/exDailyQ",
        {"startDate":"2026/10/23","endDate":"2026/11/04"},
    ),
    "TPEX_CAPITAL_REDUCTION_RESUME": (
        "https://www.tpex.org.tw/www/zh-tw/bulletin/revivt",
        {"startDate":"2026/10/23","endDate":"2026/11/04"},
    ),
}


def summarize(name: str, payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError(f"{name}: non-object response")
    keys=list(payload)
    tables=payload.get("tables")
    data=payload.get("data")
    data_count=len(data) if isinstance(data,list) else None
    table_count=sum(len(t.get("data") or []) for t in tables if isinstance(t,dict)) if isinstance(tables,list) else None
    response_range = {
        "requested_start": "20261023",
        "requested_end": "20261104",
        "reported_start": str(payload.get("strDate") or "").replace("/", ""),
        "reported_end": str(payload.get("endDate") or "").replace("/", ""),
    } if name.startswith("TWSE_EXRIGHT") else None
    range_verified = (
        response_range["reported_start"] == response_range["requested_start"]
        and response_range["reported_end"] == response_range["requested_end"]
    ) if response_range else None
    return {
        "source_range": response_range,
        "source_range_verified": range_verified,
        "source":name,
        "response_keys":keys[:30],
        "response_stat":payload.get("stat"),
        "response_date":payload.get("date"),
        "data_count":data_count,
        "table_count":table_count,
        "table_headers":[t.get("fields") for t in tables[:3] if isinstance(t,dict)] if isinstance(tables,list) else [],
        "data_sample_keys":list(data[0])[:30] if isinstance(data,list) and data and isinstance(data[0],dict) else None,
        "has_records": bool(data_count or table_count),
    }


def collect(out_dir: str):
    folder=Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    summaries={}
    for key,(url,params) in SOURCES.items():
        try:
            obj=get_json(url,params=params,timeout=25,retries=2)
            raw=json.dumps(obj,ensure_ascii=False,sort_keys=True).encode("utf-8")
            (folder/f"{key}.json").write_bytes(raw)
            summaries[key]={**summarize(key,obj),"sha256":hashlib.sha256(raw).hexdigest()}
        except Exception as exc:
            summaries[key]={"source":key,"status":"SOURCE_UNVERIFIED","error":f"{type(exc).__name__}: {str(exc)[:260]}"}
    twse_ok = any(s.get("source_range_verified") is True
                  for k,s in summaries.items() if k.startswith("TWSE_EXRIGHT"))
    manifest={
        "twse_exright_requested_range_verified":twse_ok,
        "twse_range_status":"VERIFIED" if twse_ok else "TWSE_RANGE_NOT_VERIFIED_DO_NOT_ASSUME_NO_ACTIONS",
        "schema_version":"SWING_CA_SOURCE_PROBE_1",
        "period":["2026-10-23","2026-11-04"],
        "sources":summaries,
        "status":"CORPORATE_ACTION_AUDIT_PENDING",
        "explicit_exclusions":["TWSE TWT49U may omit capital reductions/splits",
                               "No source response alone proves no corporate actions",
                               "Official latest-only OpenAPI feeds cannot prove past complete PIT history"],
        "production_eligible":False,
        "swing_v11_signal_eligible":False,
    }
    (folder/"ca_probe_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))
    return manifest


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    collect(args.out)


if __name__=="__main__":
    main()
