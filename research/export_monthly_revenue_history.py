from __future__ import annotations
import argparse, io, json, re, time, urllib.request
from pathlib import Path
import pandas as pd

def fnum(x):
    try:
        if x is None:return None
        s=str(x).strip().replace(",","").replace("%","")
        if s in ("","nan","NaN","None","--","-"):return None
        return float(s)
    except Exception:return None

def fetch_month(year,month,market,foreign,timeout=12):
    ry=year-1911
    kind="sii" if market=="TWSE" else "otc"
    suffix=1 if foreign else 0
    url=f"https://mopsov.twse.com.tw/nas/t21/{kind}/t21sc03_{ry}_{month}_{suffix}.html"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read()
    text=raw.decode("big5",errors="ignore")
    tables=pd.read_html(io.StringIO(text))
    out=[]
    for t in tables:
        if isinstance(t.columns,pd.MultiIndex):
            t.columns=["".join(str(x) for x in c if str(x)!="nan").strip() for c in t.columns]
        else:
            t.columns=[str(c).strip() for c in t.columns]
        cols=list(t.columns)
        code_col=next((c for c in cols if "公司代號" in c),None)
        rev_col=next((c for c in cols if "當月營收" in c and "累計" not in c),None)
        prev_col=next((c for c in cols if "上月營收" in c),None)
        ly_col=next((c for c in cols if "去年當月營收" in c),None)
        mom_col=next((c for c in cols if "上月比較" in c and "增減" in c),None)
        yoy_col=next((c for c in cols if "去年同月" in c and "增減" in c),None)
        cum_yoy_col=next((c for c in cols if "前期比較" in c and "增減" in c),None)
        if not code_col or not rev_col: continue
        for _,r in t.iterrows():
            code=re.sub(r"\.0$","",str(r.get(code_col,"")).strip())
            if not re.fullmatch(r"\d{4,6}",code): continue
            rev=fnum(r.get(rev_col))
            if rev is None: continue
            out.append({
                "symbol":code,"year":year,"month":month,"market":market,"foreign":foreign,
                "revenue":rev,
                "prev_revenue":fnum(r.get(prev_col)) if prev_col else None,
                "last_year_revenue":fnum(r.get(ly_col)) if ly_col else None,
                "mom":fnum(r.get(mom_col)) if mom_col else None,
                "yoy":fnum(r.get(yoy_col)) if yoy_col else None,
                "cum_yoy":fnum(r.get(cum_yoy_col)) if cum_yoy_col else None,
                "source_url":url
            })
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--year",type=int,required=True)
    ap.add_argument("--market",choices=["TWSE","TPEx"],required=True)
    ap.add_argument("--end-month",type=int,default=12)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=[];fail=[]
    for m in range(1,args.end_month+1):
        for foreign in (False,True):
            try:
                xs=fetch_month(args.year,m,args.market,foreign)
                rows.extend(xs)
                print(f"OK {args.year}-{m:02d} {args.market} foreign={foreign} rows={len(xs)}",flush=True)
            except Exception as e:
                fail.append({"year":args.year,"month":m,"market":args.market,"foreign":foreign,"error":repr(e)})
                print(f"FAIL {args.year}-{m:02d} {args.market} foreign={foreign}: {e!r}",flush=True)
            time.sleep(0.15)
    df=pd.DataFrame(rows)
    df.to_csv(out/"monthly_revenue.csv",index=False,encoding="utf-8-sig")
    (out/"failures.json").write_text(json.dumps(fail,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"manifest.json").write_text(json.dumps({
        "year":args.year,"market":args.market,"rows":len(rows),"failures":len(fail),
        "end_month":args.end_month
    },ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"rows":len(rows),"failures":len(fail)},ensure_ascii=False))
if __name__=="__main__":main()
