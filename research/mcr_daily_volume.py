"""Same-session official end-of-day traded-share enrichment for MCR research.

TWSE STOCK_DAY_ALL / TPEx mainboard daily close quotes publish latest session.
Never label an unverified quote date or previous session as today's volume.
Unavailable data is NULL, not zero. One read per exchange, not per symbol.
"""
from __future__ import annotations
import json
import math
from datetime import date
from urllib.request import Request, urlopen

SOURCES = {
    "TWSE": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
    "TPEx": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
}
MAX_BYTES = 12_000_000
KEYS = {
    "TWSE": {
        "symbol": ("Code", "證券代號"),
        "date": ("Date", "日期"),
        "volume": ("TradeVolume", "成交股數"),
    },
    "TPEx": {
        "symbol": ("SecuritiesCompanyCode",),
        "date": ("Date",),
        "volume": ("TradingShares",),
    },
}
def _field(row, keys):
    for key in keys:
        if key in row:
            return row[key]
    raise ValueError("VOLUME_SOURCE_FIELD_MISSING")

def _date(value):
    s = str(value).strip().replace("/", "").replace("-", "")
    if len(s) == 7 and s.isdecimal():
        return date(int(s[:3]) + 1911, int(s[3:5]), int(s[5:]))
    if len(s) == 8 and s.isdecimal():
        return date(int(s[:4]), int(s[4:6]), int(s[6:]))
    raise ValueError("VOLUME_DATE_NOT_VERIFIABLE")

def _shares(value):
    if isinstance(value, bool):
        raise ValueError("INVALID_VOLUME")
    txt = str(value).strip().replace(",", "")
    if txt in ("", "-", "--", "N/A", "X"):
        return None
    if not txt.isdecimal():
        raise ValueError("INVALID_VOLUME")
    return int(txt)

def fetch(market):
    if market not in SOURCES:
        raise ValueError("UNSUPPORTED_MARKET")
    with urlopen(Request(SOURCES[market], headers={
        "Accept": "application/json", "User-Agent": "Sky-MCR-daily-volume/1.0"
    }), timeout=25) as response:
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("VOLUME_PAYLOAD_TOO_LARGE")
    return json.loads(payload)

def parse_market(payload, market, expected_day):
    if market not in KEYS or not isinstance(payload, list) or len(payload) < 300:
        raise ValueError("VOLUME_MARKET_COVERAGE_LOW")
    cols = KEYS[market]
    found, sessions = {}, set()
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("VOLUME_INVALID_ROW")
        day = _date(_field(row, cols["date"]))
        sessions.add(day)
        sid = str(_field(row, cols["symbol"])).strip()
        if not sid.isdecimal() or len(sid) != 4:
            continue
        shares = _shares(_field(row, cols["volume"]))
        if sid in found:
            raise ValueError("VOLUME_DUPLICATE_CODE")
        if shares is not None:
            found[sid] = shares
    if sessions != {expected_day}:
        raise ValueError("VOLUME_TRADING_DATE_MISMATCH")
    if len(found) < 300:
        raise ValueError("VOLUME_VALID_STOCK_COVERAGE_LOW")
    return found

def enrich_merged(merged, snapshots):
    """Use only same-day verified volume; per-market errors stay unavailable."""
    if merged.get("coverage") != "TWSE_TPEX_VERIFIED" or merged.get("data_quality") != "BOTH_MARKETS_PASSED":
        raise ValueError("INVALID_MCR_SOURCE")
    day = date.fromisoformat(merged["margin_data_date"])
    counts = {"TWSE": 0, "TPEx": 0}
    for market in counts:
        if market in snapshots:
            counts[market] = len(snapshots[market])
    out = json.loads(json.dumps(merged))
    out["volume_unit"] = "shares"
    out["volume_source_status"] = {
        market: "VERIFIED" if market in snapshots else "UNAVAILABLE"
        for market in counts
    }
    out["volume_data_date"] = day.isoformat()
    for row in out["rows"]:
        market = row["exchange"]
        volume = snapshots.get(market, {}).get(row["stock_id"])
        row["daily_volume_shares"] = volume
        row["daily_volume_date"] = day.isoformat() if volume is not None else None
        row["daily_volume_source"] = SOURCES[market] if volume is not None else None
        row["daily_volume_verified"] = volume is not None
        row["trade_eligible"] = False
    return out

def collect_and_enrich(merged, fetcher=fetch):
    day = date.fromisoformat(merged["margin_data_date"])
    snapshots = {}
    errors = {}
    for market in ("TWSE", "TPEx"):
        try:
            snapshots[market] = parse_market(fetcher(market), market, day)
        except (ValueError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            errors[market] = str(exc)[:120]
    out = enrich_merged(merged, snapshots)
    out["volume_source_errors"] = errors
    return out

if __name__ == "__main__":
    from pathlib import Path
    p = Path("research_output/mcr_official_proxy_combined_latest.json")
    result = collect_and_enrich(json.loads(p.read_text(encoding="utf-8")))
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("VOLUME_STATUS", result["volume_source_status"])
    print("VOLUME_MATCHED", sum(r["daily_volume_verified"] for r in result["rows"]))
