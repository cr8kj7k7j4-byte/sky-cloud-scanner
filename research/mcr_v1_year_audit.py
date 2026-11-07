"""One-year historical MCR data-access preflight. Never substitutes missing data."""
import calendar
import json
import os
import sys
from collections import Counter
from datetime import date, timedelta, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

START = date(2025, 11, 10)
END = date(2026, 11, 6)
ROOT = Path("research_output/mcr_v1_year")
API = "https://api.finmindtrade.com/api/v4/data"

def get(dataset, token, **params):
    args = {"dataset": dataset, **params}
    url = API + "?" + urlencode(args)
    req = Request(url, headers={"Authorization": "Bearer " + token, "Accept":"application/json"})
    with urlopen(req, timeout=90) as response:
        body = json.load(response)
    if body.get("status") != 200 or not isinstance(body.get("data"), list):
        raise RuntimeError("NON_SUCCESS_DATA_RESPONSE_" + str(body.get("status")))
    return body["data"]

def months(begin, end):
    cursor = begin.replace(day=1)
    while cursor <= end:
        last = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
        yield max(cursor,begin), min(last,end)
        cursor = (last + timedelta(days=1)).replace(day=1)

def base_report():
    return {"model":"Sky MCR V1.0", "status":"INSUFFICIENT_DATA", "start":str(START),
        "end":str(END), "margin_days":0, "candidate_days":0,
        "candidate_symbol_days":0, "tick_probe_rows":0, "tick_probe":None,
        "backtest_trades":None, "net_expectancy":None, "profit_factor":None,
        "reason":None, "data_source":"FinMind Sponsor historical data (requires entitlement)"}

def run(token, getter=get):
    report = base_report()
    if not token:
        report["reason"] = "FINMIND_TOKEN_NOT_CONFIGURED"
        return report
    all_rows = []
    try:
        for start, end in months(START, END):
            batch = getter("TaiwanStockMarginMaintenance", token,
                           start_date=str(start), end_date=str(end))
            all_rows.extend(batch)
    except HTTPError as exc:
        report["reason"] = "MARGIN_ACCESS_FAILED_HTTP_" + str(exc.code)
        return report
    except (URLError, OSError, TimeoutError, RuntimeError) as exc:
        report["reason"] = "MARGIN_ACCESS_FAILED_" + type(exc).__name__
        return report
    days = set()
    candidates = []
    invalid = 0
    for row in all_rows:
        try:
            day = date.fromisoformat(str(row["date"]))
            stock = str(row["stock_id"])
            if not START <= day <= END: continue
            days.add(day)
            if len(stock) != 4 or not stock.isdigit(): continue
            ratio = float(row["margin_maintenance"])
            balance = float(row["margin_balance"])
            if 0 < ratio < 130 and balance >= 100:
                candidates.append({"date":str(day), "symbol":stock,
                                   "margin_maintenance":ratio, "margin_balance":balance})
        except (KeyError, ValueError, TypeError):
            invalid += 1
    report.update(margin_days=len(days),
                  candidate_days=len({r["date"] for r in candidates}),
                  candidate_symbol_days=len(candidates), invalid_rows=invalid)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT/"candidate_universe.json").write_text(json.dumps(candidates,ensure_ascii=False), encoding="utf-8")
    if not days or not candidates:
        report["reason"]="MISSING_MARGIN_DAYS_OR_CANDIDATES"
        return report
    # Historical tick access check for a real eligible symbol/day; do not claim strategy replay.
    first = candidates[len(candidates)//2]
    try:
        ticks = getter("TaiwanStockPriceTick", token, data_id=first["symbol"],
                       start_date=first["date"])
        report["tick_probe"]={"date":first["date"],"symbol":first["symbol"]}
        report["tick_probe_rows"]=len(ticks)
        if not ticks:
            report["reason"]="HISTORICAL_TICK_EMPTY"
            return report
    except (HTTPError,URLError,OSError,TimeoutError,RuntimeError) as exc:
        report["reason"]="TICK_ACCESS_FAILED_"+type(exc).__name__
        return report
    report["status"]="DATA_PARTIAL"
    report["reason"]="MODEL_S2_S4_PIT_FEATURES_AND_EXECUTION_COST_NOT_CONNECTED; YEAR_BACKTEST_NOT_YET_EVALUABLE"
    return report

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    report=run(os.getenv("FINMIND_TOKEN", "").strip())
    (ROOT/"data_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    lines=["# Sky MCR V1.0｜近一年回測資料驗收", "",
           f"- 期間：{START}～{END}",
           f"- 結果：**{report['status']}**",
           f"- 原因：{report['reason']}",
           f"- 有融資紀錄日數：{report['margin_days']}",
           f"- 維持率<130% 且融資餘額>=100張的股票日：{report['candidate_symbol_days']}",
           f"- 歷史逐筆抽查筆數：{report['tick_probe_rows']}", "",
           "**不可宣稱已完成交易回測**。缺少完整逐筆/盤中價格結構、先驗買盤與賣壓、當時交易資格、成交成本/可成交性時，不得補造交易。",
           "本次尚無淨期望值、PF、勝率、交易筆數等績效結論。"]
    (ROOT/"summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
