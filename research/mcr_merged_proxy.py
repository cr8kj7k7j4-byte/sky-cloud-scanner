"""Only combine fully verified, same-session TWSE + TPEx financing proxy feeds."""
from __future__ import annotations
from datetime import datetime, date
import json
from pathlib import Path
from zoneinfo import ZoneInfo

def merge_feeds(twse, tpex):
    if twse.get("data_quality")!="TWSE_PASSED_TPEX_NOT_CHECKED" or tpex.get("data_quality")!="TPEX_PASSED":
        raise ValueError("BOTH_MARKET_SOURCES_NOT_VERIFIED")
    if twse.get("mode")!="RESEARCH_PROXY_ONLY" or tpex.get("mode")!="RESEARCH_PROXY_ONLY":
        raise ValueError("NOT_RESEARCH_PROXY")
    day=twse.get("margin_data_date")
    if not day or day!=tpex.get("margin_data_date"): raise ValueError("SOURCE_SESSION_MISMATCH")
    date.fromisoformat(day)
    all_rows=[]
    for feed, market in ((twse,"TWSE"),(tpex,"TPEx")):
        rows=feed.get("rows")
        if not isinstance(rows,list) or len(rows)!=feed.get("total"):
            raise ValueError("TRUNCATED_MARKET_ROWS")
        for r in rows:
            if r.get("exchange")!=market or r.get("margin_data_date")!=day or r.get("maintenance_below_130_verified") is not False or r.get("trade_eligible") is not False:
                raise ValueError("INVALID_MARKET_ROW")
            all_rows.append(r)
    if len({x["stock_id"] for x in all_rows})!=len(all_rows):
        raise ValueError("DUPLICATE_CROSS_MARKET_STOCK")
    all_rows.sort(key=lambda x:(-x["two_session_reduction_pct"],-x["margin_balance_current_units"],x["stock_id"]))
    return {
      "schema":2, "mode":"RESEARCH_PROXY_ONLY","source":"TWSE+TPEx",
      "coverage":"TWSE_TPEX_VERIFIED", "data_quality":"BOTH_MARKETS_PASSED",
      "margin_data_date":day,"observed_at":datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
      "market_counts":{"TWSE":twse["total"],"TPEx":tpex["total"]},
      "total":len(all_rows),"rows":all_rows,"no_trade_without_validation":True,
      "maintenance_below_130_verified":False,
      "note":"融資餘額下降代理研究；不是維持率<130%、正期望值或交易訊號。"
    }

def main():
    out=Path("research_output/mcr_official_proxy_combined_latest.json")
    twse=json.loads(Path("research_output/mcr_official_proxy.json").read_text(encoding="utf-8"))
    tpex=json.loads(Path("research_output/mcr_tpex_proxy_audit.json").read_text(encoding="utf-8"))
    merged=merge_feeds(twse,tpex)
    out.write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding="utf-8")
    print("MCR_COMBINED_VERIFIED",merged["total"],merged["margin_data_date"],merged["market_counts"])

if __name__=="__main__":main()
