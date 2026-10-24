from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-root",required=True)
    ap.add_argument("--out",default="research_output_revenue_merged")
    args=ap.parse_args()
    root=Path(args.input_root);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)

    csvs=sorted(root.rglob("monthly_revenue.csv"))
    manifests=sorted(root.rglob("manifest.json"))
    failures=sorted(root.rglob("failures.json"))

    frames=[];manifest_rows=[];failure_rows=[]
    for p in csvs:
        try:
            df=pd.read_csv(p,dtype={"symbol":str})
            if not df.empty:frames.append(df)
        except Exception as e:
            failure_rows.append({"source_file":str(p),"error":repr(e),"stage":"read_csv"})
    for p in manifests:
        try:
            x=json.loads(p.read_text(encoding="utf-8"))
            x["source_file"]=str(p);manifest_rows.append(x)
        except Exception as e:
            failure_rows.append({"source_file":str(p),"error":repr(e),"stage":"read_manifest"})
    for p in failures:
        try:
            xs=json.loads(p.read_text(encoding="utf-8"))
            for x in xs:
                x["source_file"]=str(p);failure_rows.append(x)
        except Exception as e:
            failure_rows.append({"source_file":str(p),"error":repr(e),"stage":"read_failures"})

    if frames:
        all_df=pd.concat(frames,ignore_index=True)
        all_df["symbol"]=all_df["symbol"].astype(str).str.replace(r"\.0$","",regex=True)
        before=len(all_df)
        all_df=all_df.sort_values(["symbol","year","month","market","foreign"])
        all_df=all_df.drop_duplicates(["symbol","year","month"],keep="first")
        after=len(all_df)
    else:
        all_df=pd.DataFrame();before=after=0

    all_df.to_csv(out/"monthly_revenue_merged.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(manifest_rows).to_csv(out/"shard_manifests.csv",index=False,encoding="utf-8-sig")
    (out/"failures_merged.json").write_text(json.dumps(failure_rows,ensure_ascii=False,indent=2),encoding="utf-8")

    coverage=[]
    if not all_df.empty:
        g=all_df.groupby(["year","month"]).agg(
            symbols=("symbol","nunique"),
            rows=("symbol","size")
        ).reset_index()
        coverage=g.to_dict("records")
        g.to_csv(out/"coverage_by_month.csv",index=False,encoding="utf-8-sig")

    report={
        "csv_files":len(csvs),
        "manifest_files":len(manifests),
        "failure_files":len(failures),
        "rows_before_dedup":before,
        "rows_after_dedup":after,
        "failure_count":len(failure_rows),
        "coverage_months":len(coverage),
        "min_symbols_per_month":min((x["symbols"] for x in coverage),default=0),
        "max_symbols_per_month":max((x["symbols"] for x in coverage),default=0),
        "expected_shards":8,
        "complete_shard_count":sum(1 for x in manifest_rows if x.get("failures")==0),
        "validation_pass":bool(len(manifest_rows)==8 and len(failure_rows)==0 and len(coverage)>=45)
    }
    (out/"merge_validation_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=[
        "# Sky Monthly Revenue Merge Validation",
        f"- CSV shards: {report['csv_files']}/8",
        f"- Manifests: {report['manifest_files']}/8",
        f"- Rows before/after dedup: {before}/{after}",
        f"- Failures: {report['failure_count']}",
        f"- Coverage months: {report['coverage_months']}",
        f"- Symbols/month min-max: {report['min_symbols_per_month']}-{report['max_symbols_per_month']}",
        f"- Validation pass: **{report['validation_pass']}**"
    ]
    (out/"merge_validation_summary.md").write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines))

if __name__=="__main__":main()
