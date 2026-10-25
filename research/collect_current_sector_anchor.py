from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from src.industry_codes import normalize_sector

TWSE_URL="https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_URL="https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"

SECTOR_KEYS=(
    "產業別","產業類別","產業別名稱","Industry","IndustryName",
    "SecuritiesIndustryCode","SecuritiesIndustryName",
)
SYMBOL_KEYS=("公司代號","股票代號","證券代號","Code","SecuritiesCompanyCode")
NAME_KEYS=("公司簡稱","公司名稱","證券名稱","Name","CompanyName")


def _pick(row,keys):
    for k in keys:
        if row.get(k) not in (None,""):
            return row.get(k)
    return None


def parse_rows(rows,exchange,source_url,source_as_of):
    out=[]; missing_sector=[]
    for row in rows or []:
        symbol=str(_pick(row,SYMBOL_KEYS) or "").strip()
        if not (len(symbol)==4 and symbol.isdigit()):
            continue
        raw_sector=str(_pick(row,SECTOR_KEYS) or "").strip()
        if not raw_sector:
            missing_sector.append(symbol)
            continue
        sector_code,sector_name=normalize_sector(raw_sector)
        if not sector_code:
            missing_sector.append(symbol)
            continue
        out.append({
            "symbol":symbol,
            "exchange":exchange,
            "name":str(_pick(row,NAME_KEYS) or "").strip(),
            "sector_code":sector_code,
            "sector":sector_name,
            "sector_source_value":raw_sector,
            "source":source_url,
            "source_as_of":source_as_of,
        })
    return out,missing_sector


def collect(request_get=requests.get):
    as_of=datetime.now().astimezone().isoformat()
    all_rows=[]; health=[]
    for exchange,url in (("TWSE",TWSE_URL),("TPEx",TPEX_URL)):
        try:
            r=request_get(url,timeout=30,headers={"User-Agent":"sky-cloud-scanner/1.0"})
            r.raise_for_status()
            payload=r.json()
            rows=payload if isinstance(payload,list) else []
            parsed,missing=parse_rows(rows,exchange,url,as_of)
            all_rows.extend(parsed)
            health.append({
                "exchange":exchange,"source":url,"transport_ok":True,
                "raw_rows":len(rows),"parsed_sector_rows":len(parsed),
                "missing_sector_rows":len(missing),
                "status":"PASS" if parsed and not missing else ("WARN" if parsed else "FAIL"),
                "missing_sector_symbols":missing[:200],
            })
        except Exception as exc:
            health.append({
                "exchange":exchange,"source":url,"transport_ok":False,
                "raw_rows":0,"parsed_sector_rows":0,"missing_sector_rows":0,
                "status":"FAIL","error":f"{type(exc).__name__}: {exc}",
            })
    return pd.DataFrame(all_rows),{
        "schema_version":"CURRENT_SECTOR_ANCHOR_V1_0",
        "source_as_of":as_of,
        "health":health,
        "rows":len(all_rows),
        "status":"PASS" if health and all(x["status"]=="PASS" for x in health) else "WARN",
        "pit_note":"Current anchor only. It is NOT historical PIT evidence by itself.",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",default="research_output/current_sector_anchor")
    args=ap.parse_args()
    df,report=collect()
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    df.to_csv(out/"current_sector_anchor.csv",index=False)
    (out/"current_sector_anchor_audit.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
