
from __future__ import annotations
import argparse, csv, io, json, time
from datetime import datetime
from pathlib import Path
import requests

TWSE_OPENAPI = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_OPENAPI = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
TWSE_CSV = "https://mopsfin.twse.com.tw/opendata/t187ap03_L.csv"
TPEX_CSV = "https://mopsfin.twse.com.tw/opendata/t187ap03_O.csv"
TAIEX_URL = "https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST"

UA = {"User-Agent":"Mozilla/5.0 SkyResearch/1.0"}

def clean(v):
    if v is None: return ""
    return str(v).replace("\ufeff","").strip()

def first(row, keys):
    for k in keys:
        if k in row and clean(row[k]) != "":
            return clean(row[k])
    return ""

def normalize_twse_row(row):
    return {
        "symbol": first(row, ["公司代號","CompanyCode","SecuritiesCompanyCode"]),
        "name": first(row, ["公司簡稱","CompanyAbbreviation","公司名稱"]),
        "industry_code": first(row, ["產業別","IndustryCode","SecuritiesIndustryCode"]),
        "market": "TWSE",
        "source": "TWSE_OPENAPI",
    }

def normalize_tpex_row(row):
    return {
        "symbol": first(row, ["SecuritiesCompanyCode","公司代號","CompanyCode"]),
        "name": first(row, ["CompanyAbbreviation","公司簡稱","公司名稱"]),
        "industry_code": first(row, ["SecuritiesIndustryCode","產業別","IndustryCode"]),
        "market": "TPEx",
        "source": "TPEX_OPENAPI",
    }

def parse_csv_text(text):
    # Official MOPS CSV commonly uses utf-8-sig; requests already decodes text.
    return list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))

def fetch_json(session, url, timeout=30):
    r=session.get(url,headers=UA,timeout=timeout)
    r.raise_for_status()
    j=r.json()
    if not isinstance(j,list):
        raise ValueError(f"Expected list JSON from {url}")
    return j

def fetch_company_rows(session, primary, fallback_csv):
    try:
        rows=fetch_json(session,primary)
        return rows, primary
    except Exception as e1:
        r=session.get(fallback_csv,headers=UA,timeout=30)
        r.raise_for_status()
        rows=parse_csv_text(r.text)
        if not rows:
            raise RuntimeError(f"primary failed: {e1}; CSV fallback empty")
        return rows, fallback_csv

def roc_to_iso(s):
    # e.g. 112/05/23 or 112/05/23 with whitespace
    s=clean(s)
    parts=s.split("/")
    if len(parts)!=3:
        raise ValueError(f"Unexpected ROC date: {s}")
    y,m,d=map(int,parts)
    return f"{y+1911:04d}-{m:02d}-{d:02d}"

def num(s):
    s=clean(s).replace(",","")
    if s in ("","--","---","-"): return None
    return float(s)

def parse_taiex_payload(j):
    fields=j.get("fields") or []
    data=j.get("data") or []
    if not fields or not data:
        return []
    # Current endpoint fields are usually 日期, 開盤指數, 最高指數, 最低指數, 收盤指數
    idx={clean(k):i for i,k in enumerate(fields)}
    def col(row,names):
        for n in names:
            if n in idx: return row[idx[n]]
        return None
    out=[]
    for row in data:
        ds=col(row,["日期","Date"])
        if ds is None: continue
        out.append({
            "date":roc_to_iso(ds) if "/" in clean(ds) and int(clean(ds).split("/")[0])<1911 else clean(ds).replace("/","-"),
            "open":num(col(row,["開盤指數","Opening Index","Open"])),
            "high":num(col(row,["最高指數","Highest Index","High"])),
            "low":num(col(row,["最低指數","Lowest Index","Low"])),
            "close":num(col(row,["收盤指數","Closing Index","Close"])),
        })
    return out

def month_starts(start, end):
    sy,sm=map(int,start[:7].split("-"))
    ey,em=map(int,end[:7].split("-"))
    y,m=sy,sm
    out=[]
    while (y,m)<=(ey,em):
        out.append(f"{y:04d}{m:02d}01")
        m+=1
        if m==13: y,m=y+1,1
    return out

def fetch_taiex(session,start,end,sleep_sec=1.2):
    rows=[]
    errors=[]
    for ym in month_starts(start,end):
        try:
            r=session.get(TAIEX_URL,params={"date":ym,"response":"json"},headers=UA,timeout=30)
            r.raise_for_status()
            month=parse_taiex_payload(r.json())
            rows.extend(month)
        except Exception as e:
            errors.append({"month":ym,"error":f"{type(e).__name__}: {e}"})
        time.sleep(sleep_sec)
    # Unique and date-filtered
    uniq={r["date"]:r for r in rows if start<=r["date"]<=end}
    return [uniq[d] for d in sorted(uniq)], errors

def build_industry(manifest, twse_rows, tpex_rows):
    sample=manifest.get("sample",[])
    tw={normalize_twse_row(r)["symbol"]:normalize_twse_row(r) for r in twse_rows}
    tp={normalize_tpex_row(r)["symbol"]:normalize_tpex_row(r) for r in tpex_rows}
    out=[]
    missing=[]
    for s in sample:
        sym=str(s["symbol"])
        ex=s.get("exchange")
        rec=(tw if ex=="TWSE" else tp).get(sym)
        if rec is None:
            missing.append({"symbol":sym,"exchange":ex,"name":s.get("name")})
        else:
            # Preserve manifest name for audit; source name can differ slightly.
            out.append({
                **rec,
                "manifest_name":s.get("name"),
            })
    return out, missing

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--out-dir",required=True)
    ap.add_argument("--start",default="2023-05-23")
    ap.add_argument("--end",default="2026-10-22")
    ap.add_argument("--sleep-sec",type=float,default=1.2)
    args=ap.parse_args()

    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    session=requests.Session()

    twse_rows,twse_src=fetch_company_rows(session,TWSE_OPENAPI,TWSE_CSV)
    tpex_rows,tpex_src=fetch_company_rows(session,TPEX_OPENAPI,TPEX_CSV)
    industry,missing=build_industry(manifest,twse_rows,tpex_rows)

    (out/"industry_map.json").write_text(json.dumps({
        "sources":{"TWSE":twse_src,"TPEx":tpex_src},
        "rows":industry,
        "missing":missing
    },ensure_ascii=False,indent=2),encoding="utf-8")

    taiex,taiex_errors=fetch_taiex(session,args.start,args.end,args.sleep_sec)
    with (out/"taiex_daily.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["date","open","high","low","close"])
        w.writeheader(); w.writerows(taiex)

    nonempty_industry=[r for r in industry if clean(r.get("industry_code"))]
    report={
        "expected_symbols":len(manifest.get("sample",[])),
        "industry_matched":len(industry),
        "industry_nonempty_code":len(nonempty_industry),
        "industry_missing":missing,
        "industry_sources":{"TWSE":twse_src,"TPEx":tpex_src},
        "taiex_rows":len(taiex),
        "taiex_first_date":taiex[0]["date"] if taiex else None,
        "taiex_last_date":taiex[-1]["date"] if taiex else None,
        "taiex_fetch_errors":taiex_errors,
        "validation_pass":(
            len(manifest.get("sample",[]))==100 and
            len(industry)==100 and
            len(nonempty_industry)==100 and
            len(taiex)>=700 and
            not taiex_errors
        )
    }
    (out/"export_validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report["validation_pass"]:
        raise SystemExit("Official enrichment validation failed.")

if __name__=="__main__":
    main()
