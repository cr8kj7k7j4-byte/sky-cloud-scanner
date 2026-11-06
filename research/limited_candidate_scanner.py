"""Research-only: prior-session TWSE/TPEx close pool -> bounded Fugle single quotes.

This is NOT Sky v1.4 full-market Top100, and is never an entry signal.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src import official
from src.sky_single_stock_realtime import collect

TPE = ZoneInfo("Asia/Taipei")
TWSE_DAILY = official.TWSE_UNIVERSE_URL
TPEX_DAILY = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
COMMON = re.compile(r"^[1-9][0-9]{3}$")
MAX_CANDIDATES = 20


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", "").strip())
        if not 0 < number < float("inf"):
            return None
        return number
    except (ValueError, TypeError):
        return None


def _roc_day(value):
    value = str(value or "").strip()
    if len(value) != 7 or not value.isdigit():
        raise ValueError("Official daily row missing valid 7-digit ROC date")
    return datetime(int(value[:3]) + 1911, int(value[3:5]), int(value[5:7]), tzinfo=TPE).date()


def _rows(payload, exchange, today):
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{exchange}: missing official daily rows")
    parsed = []
    dates = set()
    for row in payload:
        if not isinstance(row, dict):
            continue
        code = str(row.get("Code") if exchange == "TWSE" else row.get("SecuritiesCompanyCode") or "").strip()
        if not COMMON.fullmatch(code):
            continue
        session = _roc_day(row.get("Date"))
        dates.add(session)
        close = _number(row.get("ClosingPrice") if exchange == "TWSE" else row.get("Close"))
        turnover = _number(row.get("TradeValue") if exchange == "TWSE" else (row.get("TransactionAmount") or row.get("TradingAmount") or row.get("TradeValue")))
        # Select solely by prior-day liquidity, NOT a profitable alpha ranking.
        if close is None or turnover is None or close >= 100:
            continue
        parsed.append({"symbol": code, "exchange": exchange,
                       "prior_close": close, "prior_turnover": turnover,
                       "source_date": session.isoformat()})
    if len(dates) != 1 or not dates or next(iter(dates)) >= today:
        raise ValueError(f"{exchange}: expected exactly one prior-session date")
    if len(parsed) < 50:
        raise ValueError(f"{exchange}: too few valid prior-session liquid equities")
    return parsed, next(iter(dates))


def build_pool(twse, tpex, *, now=None, max_candidates=12):
    now = now or datetime.now(TPE)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not 1 <= max_candidates <= MAX_CANDIDATES:
        raise ValueError("bounded candidate count must be between 1 and 20")
    today = now.astimezone(TPE).date()
    tse, date_tse = _rows(twse, "TWSE", today)
    otc, date_otc = _rows(tpex, "TPEx", today)
    if date_tse != date_otc:
        raise ValueError("official TWSE/TPEx prior-close dates mismatch")
    # A global turnover sort can exclude TPEx entirely. Reserve market slots.
    # This is coverage sampling, not an alpha weight or Production ranking.
    tse = sorted(tse, key=lambda r: (-r["prior_turnover"], r["symbol"]))
    otc = sorted(otc, key=lambda r: (-r["prior_turnover"], r["symbol"]))
    twse_slots = (max_candidates + 1) // 2
    tpex_slots = max_candidates // 2
    pool = tse[:twse_slots] + otc[:tpex_slots]
    # For max_candidates=1, only TWSE can be sampled; declare that scope.
    pool.sort(key=lambda r: (-r["prior_turnover"], r["symbol"]))
    return {"official_previous_session": date_tse.isoformat(),
            "official_market_counts": {"TWSE": len(tse), "TPEx": len(otc)},
            "candidates": pool}


def run(*, now=None, max_candidates=12, loader=official.get_json,
        quote_collector=collect):
    now = now or datetime.now(TPE)
    report = {
        "schema": "SKY_LIMITED_CANDIDATE_RESEARCH_V1",
        "created_at_tpe": now.isoformat(),
        "mode": "LIMITED_PRIOR_CLOSE_LIQUIDITY_CANDIDATES",
        "scope": "NOT_FULL_MARKET_LIVE",
        "production_eligible": False,
        "trading_signal_generated": False,
        "execution_authorized": False,
        "action": "等待",
        "data_status": "BLOCKED",
        "candidate_count": 0,
        "verified_count": 0,
        "results": [],
    }
    try:
        pool = build_pool(loader(TWSE_DAILY), loader(TPEX_DAILY),
                          now=now, max_candidates=max_candidates)
        report.update(pool)
        report["candidate_count"] = len(pool["candidates"])
        for candidate in pool["candidates"]:
            evidence = quote_collector(candidate["symbol"], now=now)
            if not isinstance(evidence, dict):
                evidence = {"status": "INVALID_QUOTE_PAYLOAD"}
            # Never promote this separate candidate universe to a full-market claim.
            report["results"].append({
                "symbol": candidate["symbol"], "exchange": candidate["exchange"],
                "source_date": candidate["source_date"],
                "quote_status": evidence.get("status"),
                "last_price": evidence.get("last_price"),
                "last_trade_tpe": evidence.get("last_trade_tpe"),
                "quote_age_seconds": evidence.get("quote_age_seconds"),
                "execution_authorized": False,
                "action": "觀察" if evidence.get("status") == "REALTIME_QUOTE_VERIFIED" else "等待",
            })
        report["verified_count"] = sum(
            row["quote_status"] == "REALTIME_QUOTE_VERIFIED" for row in report["results"]
        )
        report["data_status"] = ("LIMITED_SCOPE_VERIFIED" if report["verified_count"]
                                 else "NO_VALID_SINGLE_QUOTE")
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:180]
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--out", default="output/limited_candidates/latest.json")
    args = parser.parse_args()
    report = run(max_candidates=args.max_candidates)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print(json.dumps({
        "mode": report["mode"], "status": report["data_status"],
        "official_previous_session": report.get("official_previous_session"),
        "candidate_count": report["candidate_count"],
        "verified_count": report["verified_count"],
        "production_eligible": False,
        "trading_signal_generated": False,
    }, ensure_ascii=False))
    if report["data_status"] == "BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
