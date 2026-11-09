"""Join MCR dated financing proxy with evidence-labelled current Fugle observations.

Information only. No inference, price fabrication, margin-maintenance estimate,
strategy upgrade or order. Missing live quote never removes an MCR observation.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

MCR = Path("output/mcr_observation_latest.json")
LIVE = Path("output/sky_quickscan_information/full_universe.json")
VALIDATED = Path("output/research_visibility/latest.json")
OUT = Path("output/mcr_intraday_information_latest.json")
MD = Path("output/mcr_intraday_information_latest.md")
TZ = ZoneInfo("Asia/Taipei")
PRICE_FIELDS = ("last_price", "volume", "change_pct", "last_trade_time", "time_age_seconds", "data_status")

def join(mcr, live, generated_at, accepted_evidence=None):
    source = mcr if isinstance(mcr, dict) else {}
    observation = live if isinstance(live, dict) else {}
    universe = observation.get("all_symbols")
    quotes = {
        (str(x.get("symbol")), x.get("exchange")): x
        for x in universe if isinstance(x, dict) and x.get("symbol")
    } if isinstance(universe, list) else {}
    # This independent feed contains ONLY rows previously accepted by the
    # existing same-session market executed-trade validator. It is not a
    # whole-market certificate and never changes trade_eligible.
    verified = accepted_evidence if isinstance(accepted_evidence, dict) else {}
    accepted = {}
    items = verified.get("observations")
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or item.get("data_state") != "ACCEPTED_EXECUTED_TRADE_BY_MARKET_GATE":
            continue
        try:
            valid_price = float(item.get("last"))
            if not 0 < valid_price < float("inf"): continue
        except (ValueError, TypeError, OverflowError):
            continue
        if item.get("symbol") and item.get("exchange") in ("TWSE", "TPEx"):
            accepted[(str(item["symbol"]), item["exchange"])] = item
    candidates = source.get("rows")
    rows = []
    for candidate in candidates if isinstance(candidates, list) else []:
        if not isinstance(candidate, dict): continue
        q = quotes.get((str(candidate.get("stock_id")), candidate.get("exchange")), {})
        row = dict(candidate)
        for key in PRICE_FIELDS:
            row[key] = q.get(key) if q else None
        if not q:
            row["data_status"] = "MISSING_LIVE_INFORMATION"
        row["price_source"] = q.get("source") if q else None
        row["quote_checked_at"] = observation.get("checked_at_tpe") if q else None
        a = accepted.get((str(candidate.get("stock_id")), candidate.get("exchange")))
        row["accepted_executed_price"] = float(a["last"]) if a else None
        row["accepted_executed_trade_time"] = a.get("trade_time") if a else None
        row["accepted_executed_source"] = a.get("source") if a else None
        row["accepted_executed_status"] = a.get("data_state") if a else None
        row["trade_eligible"] = False
        row["action"] = "觀察"
        row["maintenance_below_130_verified"] = False
        row["margin_maintenance_pct"] = None
        rows.append(row)
    counts = {key: sum(r.get("exchange") == key for r in rows) for key in ("TWSE","TPEx")}
    status_counts = {}
    for row in rows:
        status = row["data_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    missing = []
    if not rows: missing.append("MCR_FINANCING_CANDIDATES_UNAVAILABLE")
    if not quotes: missing.append("LIVE_ALL_MARKET_OBSERVATIONS_UNAVAILABLE")
    if not observation.get("checked_at_tpe"): missing.append("LIVE_OBSERVATION_TIME_UNAVAILABLE")
    return {
        "schema":"SKY_MCR_INTRADAY_INFORMATION_V1",
        "generated_at":generated_at,
        "margin_source_date":source.get("financing_source_date"),
        "quote_observed_at":observation.get("checked_at_tpe"),
        "official_universe_count":observation.get("universe_count"),
        "market_counts":counts,
        "candidate_count":len(rows),
        "with_observed_price":sum(r["last_price"] is not None for r in rows),
        "fresh_executed_count":status_counts.get("FRESH_EXECUTED_TRADE", 0),
        "independent_accepted_executed_count":sum(r["accepted_executed_price"] is not None for r in rows),
        "quote_status_counts":status_counts,
        "data_blockers":missing,
        "status":"RESEARCH_INFORMATION_ONLY_NO_TRADE",
        "trade_eligible":False,
        "headline":"🔴 禁止新進場、未驗證通過；仍提供所有可核對研究資訊",
        "rows":rows,
    }

def markdown(report):
    """Show every MCR observation using the fixed 13-column mobile contract.

    The user's 即時價 column is never filled from an unverified bulk snapshot.
    Unverified prices remain in JSON as last_price with their data_status.
    """
    columns = (
        "股票代碼", "股票名稱", "即時價", "分類", "方向", "多方評分",
        "空方評分", "買進觸發", "最高接受價", "停損／失效",
        "現在動作", "加碼價格", "停利價格",
    )
    lines = [
        "# Sky 融資清洗反轉｜全候選資訊觀察（研究用途）", "",
        "融資資料日期：" + str(report.get("margin_source_date") or "待確認"),
        "行情觀察時間：" + str(report.get("quote_observed_at") or "待確認"),
        "研究候選：" + str(report.get("candidate_count", 0)) +
        " 檔；有價格觀察：" + str(report.get("with_observed_price", 0)) +
        " 檔；富果已驗證逐股成交：" + str(report.get("fresh_executed_count", 0)) +
        " 檔；獨立已驗證成交：" + str(report.get("independent_accepted_executed_count", 0)) + " 檔",
        "即時價僅呈現已驗證當日成交；未驗證的快照價留在 JSON，不冒稱即時。",
        "全部研究候選均保留，缺少資訊時填「待確認」，不虛構分數、交易價或維持率。", "",
        "|" + "|".join(columns) + "|",
        "|" + "|".join(":---:" for _ in columns) + "|",
    ]
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Even independently accepted executed prices are informational only.
        # Match the independently verified price to this observation's market.
        price = row.get("accepted_executed_price")
        if price is None and row.get("data_status") == "FRESH_EXECUTED_TRADE":
            price = row.get("last_price")
        verified_price = (
            f"{price:,.2f}" if isinstance(price, (float, int))
            and not isinstance(price, bool) and 0 < price < float("inf")
            else "待確認"
        )
        values = (
            str(row.get("stock_id") or "待確認"),
            str(row.get("stock_name") or "待確認"),
            verified_price, "X", "不交易", "—", "—",
            "待確認", "待確認", "待確認", "觀察",
            "待確認", "待確認",
        )
        lines.append("|" + "|".join(v.replace("|", "／").replace("\n", " ") for v in values) + "|")
    if not rows:
        lines.append("|—|暫無可核對候選（資料待確認）|待確認|X|不交易|—|—|待確認|待確認|待確認|等待|待確認|待確認|")
    lines.extend([
        "",
        "未驗證快照價格、融資降幅、成交量、資料時間與資料狀態，請查 JSON 明細：",
        "output/mcr_intraday_information_latest.json",
        "融資餘額降幅不代表個股融資維持率低於130%；未確認反轉觸發條件。",
        "**🔴 禁止新進場、未驗證通過；資訊提供使用者自主判斷，不代表交易資格。**",
    ])
    return "\n".join(lines) + "\n"

def main():
    def load(p):
        try: return json.loads(p.read_text(encoding="utf-8"))
        except (OSError,ValueError): return None
    r=join(load(MCR),load(LIVE),datetime.now(TZ).isoformat(),load(VALIDATED))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    MD.write_text(markdown(r),encoding="utf-8")
    print("MCR_INTRADAY_INFORMATION",r["candidate_count"],"priced",r["with_observed_price"],"fresh",r["fresh_executed_count"],"accepted_independent",r["independent_accepted_executed_count"],"blockers",r["data_blockers"])

if __name__=="__main__": main()
