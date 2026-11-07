"""Official TWSE margin-balance reduction proxy, NOT margin maintenance.

No synthetic 130% estimates or trade signals. Fail closed on absent per-session
date evidence, missing fields, unexpected units, or partial coverage.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
URL = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
CODE = re.compile(r"^[0-9]{4}$")
MIN_ROWS = 500

def fetch(session):
    url = URL + "?" + urlencode({"date": session.strftime("%Y%m%d"), "selectType": "ALL", "response": "json"})
    with urlopen(Request(url, headers={"User-Agent": "Sky-research-official-margin-audit/1.0",
                                        "Accept": "application/json"}), timeout=25) as response:
        return json.load(response)

def _n(value):
    if isinstance(value, bool): return None
    try:
        s = str(value).strip().replace(",", "")
        if not s or s in ("--", "-", "N/A"): return None
        v = int(s)
        return v if v >= 0 else None
    except (TypeError, ValueError): return None

def _session(value):
    """Accept explicit ISO/ROC/exchange date only, never infer from HTTP request."""
    text = str(value or "").strip().replace("/", "").replace("-", "")
    if len(text) == 8 and text.isdigit():
        try: return date(int(text[:4]), int(text[4:6]), int(text[6:]))
        except ValueError: return None
    if len(text) == 7 and text.isdigit():
        try: return date(int(text[:3])+1911, int(text[3:5]), int(text[5:]))
        except ValueError: return None
    return None

def parse_twse(payload, expected_day):
    if not isinstance(payload, dict) or payload.get("stat") != "OK":
        raise ValueError("TWSE_SOURCE_NOT_OK")
    # Original dated RWD response must identify its own session, not just requested date.
    actual = _session(payload.get("date"))
    if actual != expected_day:
        raise ValueError("TWSE_SESSION_DATE_MISMATCH_OR_UNKNOWN")
    tables = payload.get("tables") or []
    if not isinstance(tables, list): raise ValueError("TWSE_TABLES_MISSING")
    parsed = {}
    for table in tables:
        fields, rows = table.get("fields", []), table.get("data", [])
        if not isinstance(fields, list) or not isinstance(rows, list): continue
        normalized = [str(x).strip().replace(" ", "") for x in fields]
        # Repeated '前日餘額' / '今日餘額': first pair is financing, second is lending.
        code_idx = next((i for i, x in enumerate(normalized) if x in ("股票代號","證券代號","代號")), None)
        prevs = [i for i, x in enumerate(normalized) if "前日餘額" in x]
        today = [i for i, x in enumerate(normalized) if "今日餘額" in x or "當日餘額" in x]
        if code_idx is None or not prevs or not today: continue
        name_idx = next((i for i,x in enumerate(normalized) if x in ("股票名稱","證券名稱","名稱")), None)
        for row in rows:
            if not isinstance(row, list) or max(code_idx, prevs[0], today[0]) >= len(row): continue
            sid = str(row[code_idx]).strip()
            if not CODE.fullmatch(sid): continue
            before, now = _n(row[prevs[0]]), _n(row[today[0]])
            if before is None or now is None: continue
            if sid in parsed: raise ValueError("DUPLICATE_STOCK_ID")
            parsed[sid] = {
                "stock_id": sid, "stock_name": str(row[name_idx]).strip() if name_idx is not None and name_idx < len(row) else "",
                "margin_balance_prev_units": before, "margin_balance_current_units": now,
                "margin_balance_delta_units": now-before,
                "margin_balance_change_pct": round((now-before)/before*100, 3) if before else None,
                "exchange": "TWSE", "margin_data_date": expected_day.isoformat(),
                "source": "TWSE_RWD_MI_MARGN", "maintenance_below_130_verified": False,
                "margin_maintenance_pct": None, "action": "觀察", "trade_eligible": False,
            }
    if len(parsed) < MIN_ROWS: raise ValueError("INSUFFICIENT_TWSE_COVERAGE")
    return parsed

def build_proxy(today_rows, previous_rows, *, report_time):
    """Proxy: largest margin balance reduction, not predicted returns."""
    if not today_rows or not previous_rows: raise ValueError("MISSING_SESSIONS")
    current_day = next(iter(today_rows.values()))["margin_data_date"]
    previous_day = next(iter(previous_rows.values()))["margin_data_date"]
    if current_day <= previous_day: raise ValueError("NON_CHRONOLOGICAL_SESSIONS")
    out = []
    for sid, current in today_rows.items():
        prev = previous_rows.get(sid)
        if not prev: continue
        b = prev["margin_balance_current_units"]
        a = current["margin_balance_current_units"]
        if b < 100 or a < 100 or a >= b: continue
        # Exclude tiny reductions; this is a screening proxy, not an efficacy threshold.
        drop = (b-a)/b*100
        if drop < 5: continue
        out.append({**current, "previous_session_balance_units": b,
                    "two_session_reduction_pct": round(drop,3),
                    "proxy_reason": "融資餘額下降，尚未證實賣壓衰竭或價格反轉",
                    "reversal_score": None, "net_expectancy_per_trade_pct": None})
    out.sort(key=lambda x: (-x["two_session_reduction_pct"], -x["margin_balance_current_units"], x["stock_id"]))
    return {"schema": 1, "mode": "RESEARCH_PROXY_ONLY", "source": "TWSE",
            "coverage": "TWSE_ONLY_TPEX_NOT_VERIFIED", "margin_data_date": current_day,
            "previous_margin_data_date": previous_day, "observed_at": report_time,
            "sort_effective": "margin_reduction", "total": len(out), "rows": out,
            "maintenance_below_130_verified": False, "no_trade_without_validation": True,
            "note": "融資餘額減少≠個股維持率<130%；不是正期望值或反轉確認。"}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="research_output/mcr_official_proxy.json")
    parser.add_argument("--date", help="date YYYY-MM-DD, default last weekday (not guaranteed exchange session)")
    args = parser.parse_args()
    now = datetime.now(TZ)
    target = date.fromisoformat(args.date) if args.date else now.date()
    while target.weekday() >= 5: target -= timedelta(days=1)
    # The prior exchange trading day is determined by source contents; weekends skipped.
    previous = target-timedelta(days=1)
    while previous.weekday() >= 5: previous -= timedelta(days=1)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = parse_twse(fetch(target), target)
        before = parse_twse(fetch(previous), previous)
        result = build_proxy(current, before, report_time=now.isoformat())
        result["data_quality"] = "TWSE_PASSED_TPEX_NOT_CHECKED"
    except Exception as exc:
        # No fabricated empty list: explicit audit failure.
        result = {"schema":1,"mode":"RESEARCH_PROXY_ONLY",
                  "data_quality":"BLOCKED_EXTERNAL_DATA",
                  "reason":type(exc).__name__ + ":" + str(exc)[:140],
                  "total":None,"rows":[],"no_trade_without_validation":True,
                  "maintenance_below_130_verified":False,
                  "observed_at":now.isoformat()}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MCR official proxy:",result["data_quality"],"rows:",result["total"])
    if result["data_quality"] == "BLOCKED_EXTERNAL_DATA":
        raise SystemExit(2)

if __name__=="__main__":main()
