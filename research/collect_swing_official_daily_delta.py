"""W3A official point-in-time Swing daily OHLCV delta collector.

Collect TWSE and TPEx latest *post-market* D-close snapshots; require
payload-record date == requested date. No intraday / prior-close substitution.
Each row is joined to an existing canonical PIT interval. A date with an
unknown event-ledger status cannot be considered adjusted-history complete.

This collector intentionally writes a delta, not a new green W1 live signal:
historical gaps and corporate action updates require separate verification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.http_utils import get_json

TWSE = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
SYMBOL = re.compile(r"^[1-9][0-9]{3}$")


def roc_day(value: object) -> str:
    s = str(value or "").strip().replace("/", "")
    if len(s) != 7 or not s.isdigit():
        raise ValueError(f"invalid ROC session date: {value!r}")
    return date(int(s[:3])+1911, int(s[3:5]), int(s[5:7])).isoformat()


def value(v: object):
    s = str(v or "").strip().replace(",", "")
    if s in ("", "-", "--", "---", "除權息"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_market(raw: object, market: str, expected_day: str) -> tuple[list[dict], dict]:
    if not isinstance(raw, list):
        raise ValueError(f"{market}: official response not array")
    keys = {
        "TWSE": ("Code", "OpeningPrice", "HighestPrice", "LowestPrice", "ClosingPrice", "TradeVolume", "TradeValue"),
        "TPEx": ("SecuritiesCompanyCode", "Open", "High", "Low", "Close", "TradingShares", "TransactionAmount"),
    }
    fields = keys[market]
    rows = []
    invalid = 0
    wrong_date = 0
    observed_dates = set()
    for x in raw:
        symbol = str(x.get(fields[0]) or "").strip()
        if not SYMBOL.fullmatch(symbol):
            continue
        try:
            d = roc_day(x.get("Date"))
        except ValueError:
            invalid += 1
            continue
        observed_dates.add(d)
        if d != expected_day:
            wrong_date += 1
            continue
        o,h,l,c,vol,turn = [value(x.get(k)) for k in fields[1:]]
        if None in (o,h,l,c,vol) or min(o,h,l,c) <= 0 or vol < 0 or not(l <= min(o,c) <= max(o,c) <= h):
            invalid += 1
            continue
        rows.append({
            "symbol": symbol, "exchange": market, "date": d,
            "open": o, "high": h, "low": l, "close": c,
            "volume": vol, "turnover": turn,
            "source": f"{market}_OFFICIAL_OPENAPI_LATEST_DAILY",
            "adjusted": False,
        })
    diag = {
        "market": market,
        "raw_common_stock_rows": len(rows)+invalid+wrong_date,
        "valid_date_rows": len(rows),
        "invalid_rows": invalid,
        "wrong_date_rows": wrong_date,
        "observed_dates": sorted(observed_dates),
        "requested_date": expected_day,
    }
    if len(rows) < (500 if market == "TWSE" else 400):
        raise ValueError(f"{market} insufficient valid dated OHLCV: {diag}")
    return rows, diag


def join_pit(rows: list[dict], intervals: list[dict]) -> tuple[list[dict], list[dict]]:
    indexed = {}
    for interval in intervals:
        indexed.setdefault(str(interval.get("symbol") or ""), []).append(interval)
    joined = []
    quarantined = []
    for row in rows:
        sym, d = row["symbol"], row["date"]
        found = [
            iv for iv in indexed.get(sym, [])
            if iv.get("exchange") == row["exchange"]
            and str(iv.get("listed_from") or "") <= d
            and (not iv.get("listed_to") or str(iv["listed_to"]) >= d)
        ]
        if len(found) != 1:
            quarantined.append({"symbol":sym,"exchange":row["exchange"],"date":d,"matches":len(found)})
            continue
        joined.append({**row,"pit_listed_from":found[0]["listed_from"],"pit_listed_to":found[0].get("listed_to")})
    return joined, quarantined


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date",required=True)
    ap.add_argument("--pit-json",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    day = args.date
    if day != "auto":
        day = date.fromisoformat(day).isoformat()
    pit=json.loads(Path(args.pit_json).read_text(encoding="utf-8"))
    if pit.get("historical_universe_gate_pass") is not True or (pit.get("interval_validation") or {}).get("valid") is not True:
        raise SystemExit("canonical PIT gate not PASS")
    all_rows=[]
    diags=[]
    for market,url in (("TWSE",TWSE),("TPEx",TPEX)):
        payload=get_json(url,retries=3,timeout=30)
        if day == "auto":
            valid_dates=[]
            for row in payload if isinstance(payload,list) else []:
                if SYMBOL.fullmatch(str(row.get("Code") or row.get("SecuritiesCompanyCode") or "").strip()):
                    try:
                        valid_dates.append(roc_day(row.get("Date")))
                    except ValueError:
                        pass
            if not valid_dates:
                raise SystemExit(f"{market}: no verified official dated common stock records")
            day=max(valid_dates)
            age=(datetime.now(ZoneInfo("Asia/Taipei")).date()-date.fromisoformat(day)).days
            if not 0 <= age <= 4:
                raise SystemExit(f"official daily source stale/future: {market}={day}, age={age}")
        rows, diag=parse_market(payload,market,day)
        all_rows.extend(rows)
        diags.append(diag)
    joined, quarantined=join_pit(all_rows,pit["intervals"])
    if len(joined)<1400:
        raise SystemExit(f"daily PIT rows insufficient: {len(joined)}")
    folder=Path(args.out)
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/f"official_daily_{day}.json"
    doc={"schema_version":"SKY_SWING_OFFICIAL_DAILY_DELTA_1",
         "trading_date":day,
         "retrieved_at":datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
         "status":"RAW_PIT_DELTA_ONLY_NOT_CORPORATE_ACTION_READY",
         "session_date_verified":True,
         "markets":diags,
         "pit_matched_rows":len(joined),
         "quarantined_rows":quarantined,
         "rows":joined,
         "warnings":["Raw D-close only: do not promote to adjusted historical dataset without causal corporate action event-ledger refresh.",
                     "Latest-only endpoints cannot fill missing prior sessions retroactively."]}
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest={"schema_version":"SKY_SWING_OFFICIAL_DAILY_DELTA_MANIFEST_1",
              "status":doc["status"],"day":day,"count":len(joined),
              "sha256":sha,"file":path.name}
    (folder/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))


if __name__=="__main__":
    main()
