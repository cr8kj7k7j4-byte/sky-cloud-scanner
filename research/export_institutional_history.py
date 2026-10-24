from __future__ import annotations
import argparse, csv, json, re, time
from datetime import datetime
from pathlib import Path
import requests

TWSE_URL="https://www.twse.com.tw/rwd/zh/fund/T86"
TPEX_NEW_URL="https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"
TPEX_OLD_URL="https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php"
UA={"User-Agent":"Mozilla/5.0 SkyResearch/1.0"}

def clean(x):
    return "" if x is None else str(x).replace("\ufeff","").strip()

def n(x):
    s=clean(x).replace(",","").replace("−","-").replace("－","-").replace("＋","+")
    if s in ("","--","---","nan","None"): return 0
    if s.startswith("(") and s.endswith(")"): s="-"+s[1:-1]
    try: return int(float(s))
    except: return 0

def roc_date(iso):
    d=datetime.strptime(iso,"%Y-%m-%d").date()
    return f"{d.year-1911:03d}/{d.month:02d}/{d.day:02d}"

def read_trade_dates(path,start,end):
    with Path(path).open(encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    return sorted({clean(r["date"]) for r in rows if start<=clean(r["date"])<=end})

def read_manifest(path):
    m=json.loads(Path(path).read_text(encoding="utf-8"))
    return {(str(x["symbol"]),x["exchange"]):x for x in m["sample"]}

def find_col(fields,cands):
    norm=[re.sub(r"\s+","",clean(x)) for x in fields]
    for c in cands:
        cc=re.sub(r"\s+","",c)
        for i,x in enumerate(norm):
            if x==cc:return i
    return None

def parse_twse_json(payload,trade_date):
    if payload.get("stat") not in (None,"OK"): return []
    fields=payload.get("fields") or []; rows=payload.get("data") or []
    if not fields or not rows:return []
    idx={
      "code":find_col(fields,["證券代號"]),
      "name":find_col(fields,["證券名稱"]),
      "f":find_col(fields,["外陸資買賣超股數(不含外資自營商)"]),
      "fs":find_col(fields,["外資自營商買賣超股數"]),
      "t":find_col(fields,["投信買賣超股數"]),
      "d":find_col(fields,["自營商買賣超股數"]),
      "total":find_col(fields,["三大法人買賣超股數"])
    }
    if any(v is None for v in idx.values()):
        raise ValueError(f"Unexpected TWSE fields: {fields}")
    out=[]
    for r in rows:
        code=clean(r[idx["code"]]).replace("=","").replace('"',"")
        if not re.fullmatch(r"\d{4}",code): continue
        foreign=n(r[idx["f"]])+n(r[idx["fs"]]); trust=n(r[idx["t"]]); dealer=n(r[idx["d"]]); total=n(r[idx["total"]])
        if total!=0 and foreign+trust+dealer!=total: continue
        out.append({"date":trade_date,"symbol":code,"name":clean(r[idx["name"]]),"exchange":"TWSE",
                    "foreign_net":foreign,"trust_net":trust,"dealer_net":dealer,"total_inst_net":total,
                    "source":"TWSE_T86"})
    return out

def parse_tpex_rows(rows,trade_date,source):
    out=[]
    for r in rows:
        if not r or len(r)<24: continue
        code=clean(r[0]).replace("=","").replace('"',"")
        if not re.fullmatch(r"\d{4}",code): continue
        foreign=n(r[10]); trust=n(r[13]); dealer=n(r[22]); total=n(r[23])
        if total!=0 and foreign+trust+dealer!=total: continue
        out.append({"date":trade_date,"symbol":code,"name":clean(r[1]),"exchange":"TPEx",
                    "foreign_net":foreign,"trust_net":trust,"dealer_net":dealer,"total_inst_net":total,
                    "source":source})
    return out

def parse_tpex_new(payload,trade_date):
    tables=payload.get("tables") or []
    return parse_tpex_rows((tables[0].get("data") or []) if tables else [],trade_date,"TPEx_NEW")

def parse_tpex_old(payload,trade_date):
    return parse_tpex_rows(payload.get("aaData") or [],trade_date,"TPEx_OLD")

def fetch_twse(session,d):
    r=session.get(TWSE_URL,params={"date":d.replace("-",""),"selectType":"ALLBUT0999","response":"json"},headers=UA,timeout=30)
    r.raise_for_status()
    return parse_twse_json(r.json(),d)

def fetch_tpex(session,d):
    rd=roc_date(d)
    try:
        r=session.get(TPEX_NEW_URL,params={"type":"Daily","sect":"EW","date":rd,"id":"","response":"json"},headers=UA,timeout=30)
        r.raise_for_status()
        rows=parse_tpex_new(r.json(),d)
        if rows:return rows
    except Exception:
        pass
    r=session.get(TPEX_OLD_URL,params={"l":"zh-tw","o":"json","se":"EW","t":"D","d":rd,"s":"0,asc"},headers=UA,timeout=30)
    r.raise_for_status()
    return parse_tpex_old(r.json(),d)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True); ap.add_argument("--taiex",required=True); ap.add_argument("--out-dir",required=True)
    ap.add_argument("--start",default="2023-05-23"); ap.add_argument("--end",default="2026-10-22"); ap.add_argument("--sleep",type=float,default=.20)
    ap.add_argument("--shard-index",type=int,default=0); ap.add_argument("--shard-count",type=int,default=1)
    args=ap.parse_args()

    universe=read_manifest(args.manifest); all_dates=read_trade_dates(args.taiex,args.start,args.end)
    if not (0 <= args.shard_index < args.shard_count): raise SystemExit("invalid shard")
    dates=all_dates[args.shard_index::args.shard_count]
    outdir=Path(args.out_dir); outdir.mkdir(parents=True,exist_ok=True)
    sess=requests.Session(); all_rows=[]; failures=[]; coverage=[]
    for i,d in enumerate(dates,1):
        for ex,fn in [("TWSE",fetch_twse),("TPEx",fetch_tpex)]:
            try:
                rows=fn(sess,d); keep=[r for r in rows if (r["symbol"],ex) in universe]
                all_rows.extend(keep); coverage.append({"date":d,"exchange":ex,"market_rows":len(rows),"sample_rows":len(keep)})
            except Exception as e:
                failures.append({"date":d,"exchange":ex,"error":f"{type(e).__name__}: {e}"})
        if i%25==0: print(f"shard={args.shard_index}/{args.shard_count} {i}/{len(dates)} dates rows={len(all_rows)} failures={len(failures)}", flush=True)
        time.sleep(args.sleep)

    all_rows.sort(key=lambda r:(r["date"],r["exchange"],r["symbol"]))
    fields=["date","symbol","name","exchange","foreign_net","trust_net","dealer_net","total_inst_net","source"]
    with (outdir/"institutional_flows.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(all_rows)
    with (outdir/"daily_coverage.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["date","exchange","market_rows","sample_rows"]); w.writeheader(); w.writerows(coverage)

    report={
      "requested_trade_dates":len(dates),
      "total_trade_dates":len(all_dates),
      "shard_index":args.shard_index,
      "shard_count":args.shard_count,
      "covered_trade_dates":len({r["date"] for r in all_rows}),
      "unique_sample_symbols":len({(r["symbol"],r["exchange"]) for r in all_rows}),
      "rows":len(all_rows),
      "sources":sorted({r["source"] for r in all_rows}),
      "failure_count":len(failures),
      "failures":failures,
      "first_date":all_rows[0]["date"] if all_rows else None,
      "last_date":all_rows[-1]["date"] if all_rows else None
    }
    min_dates=max(1,int(len(dates)*0.90))
    report["validation_pass"]=(report["covered_trade_dates"]>=min_dates and
                               report["unique_sample_symbols"]>=80 and report["rows"]>=5000 and report["failure_count"]<=10)
    (outdir/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report["validation_pass"]: raise SystemExit("Institutional history validation failed")

if __name__=="__main__": main()
