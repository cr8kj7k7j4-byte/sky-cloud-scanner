"""W0 #363: manual ChatGPT position input, read-only account risk review.

No broker connection, trading ledger, market API calls or order execution.
Quote evidence MUST be supplied by an independently authorized Fugle collector.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import re
from typing import Any

from .sky_command_router import UPDATE_PRESENTATION

TPE = timezone(timedelta(hours=8))
POSITION_LINE = re.compile(
    r"^(?P<symbol>\d{4,6})\s+"
    r"(?P<quantity>\d+(?:,\d{3})*)(?P<unit>股|張)\s+"
    r"(?:成本|均價)\s*(?P<cost>\d+(?:\.\d+)?)"
    r"(?:\s+停損\s*(?P<stop>\d+(?:\.\d+)?))?\s*$"
)
ACCOUNT_FIELDS = (
    "account_equity", "daily_pnl", "open_risk",
    "concurrent_positions", "correlated_open_risk",
    "drawdown_pct", "consecutive_losses",
)
MOBILE_COLUMNS = (
    "股票", "現價", "方向", "多方評分", "空方評分", "買進觸發",
    "最高接受價", "停損／失效", "分類", "現在動作",
)


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def parse_manual_positions(message: str) -> dict:
    """Strict lines: '2330 1000股 成本850 停損800' or '2330 1張 均價850'.

    Unrecognized lines are never silently ignored or interpreted as zero.
    """
    if not isinstance(message, str):
        return {"status": "HOLD_POSITION_INPUT", "positions": [], "errors": ["INVALID_MESSAGE"]}
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if lines and lines[0] == "Sky 持股檢查":
        lines.pop(0)
    errors = []
    positions = []
    seen = set()
    if not lines:
        errors.append("MISSING_POSITIONS")
    for line in lines:
        match = POSITION_LINE.fullmatch(line)
        if match is None:
            errors.append("INVALID_POSITION_LINE")
            continue
        symbol = match["symbol"]
        if symbol in seen:
            errors.append("DUPLICATE_SYMBOL")
            continue
        seen.add(symbol)
        shares = int(match["quantity"].replace(",", ""))
        if match["unit"] == "張":
            shares *= 1000
        cost = _number(match["cost"])
        stop = _number(match["stop"])
        if shares <= 0 or cost is None or cost <= 0 or (stop is not None and stop <= 0):
            errors.append("INVALID_POSITION_VALUES")
            continue
        positions.append({"symbol": symbol, "shares": shares, "average_cost": cost, "stop": stop})
    if len(positions) > 3:
        errors.append("MAX_POSITIONS_EXCEEDED")
    return {"status": "PASS_INPUT" if not errors else "HOLD_POSITION_INPUT",
            "positions": positions, "errors": errors}


def _verified_quote(quote: Any, symbol: str, now: datetime) -> tuple[float | None, str | None]:
    """Never treat snapshot capture/lastUpdated as a real last executed trade."""
    if not isinstance(quote, dict) or quote.get("symbol") != symbol:
        return None, None
    if (quote.get("source") != "Fugle MarketData API /intraday/quote"
            or quote.get("executed_trade_verified") is not True
            or quote.get("status") != "REALTIME_QUOTE_VERIFIED"):
        return None, None
    price = _number(quote.get("last_price"))
    when = quote.get("last_trade_tpe")
    if price is None or price <= 0 or not isinstance(when, str):
        return None, None
    try:
        stamp = datetime.fromisoformat(when)
    except ValueError:
        return None, None
    if stamp.tzinfo is None or now.tzinfo is None:
        return None, None
    age = (now - stamp).total_seconds()
    if (stamp.astimezone(TPE).date() != now.astimezone(TPE).date()
            or quote.get("quote_date") != now.astimezone(TPE).date().isoformat()
            or age < -30 or age > 120):
        return None, None
    return price, stamp.astimezone(TPE).isoformat()


def review_manual_positions(
    message: str, *, quotes: dict | None = None,
    account_context: dict | None = None, now: datetime | None = None,
) -> dict:
    """Show gross mark-to-market only with verified quote; never authorize entries."""
    parsed = parse_manual_positions(message)
    now = now or datetime.now(TPE)
    if now.tzinfo is None:
        raise ValueError("NOW_TIMEZONE_REQUIRED")
    quotes = quotes if isinstance(quotes, dict) else {}
    account = account_context if isinstance(account_context, dict) else {}
    missing = [field for field in ACCOUNT_FIELDS if account.get(field) is None]
    invalid = []
    for field in ACCOUNT_FIELDS:
        value = account.get(field)
        if value is None:
            continue
        number = _number(value)
        if (number is None or
                (field != "daily_pnl" and number < 0) or
                (field in ("concurrent_positions", "consecutive_losses")
                 and not number.is_integer()) or
                (field == "account_equity" and number <= 0)):
            invalid.append(field)
    rows = []
    reasons = list(parsed["errors"])
    if missing:
        reasons.append("HOLD_MISSING_ACCOUNT_CONTEXT")
    if invalid:
        reasons.append("HOLD_INVALID_ACCOUNT_CONTEXT")
    risk_sum = 0.0
    full_risk = True
    for position in parsed["positions"]:
        symbol = position["symbol"]
        shares = position["shares"]
        cost = position["average_cost"]
        stop = position["stop"]
        price, trade_time = _verified_quote(quotes.get(symbol), symbol, now)
        if price is None:
            reasons.append("HOLD_A2_EXECUTED_TRADE_" + symbol)
        if stop is None:
            reasons.append("HOLD_STOP_" + symbol)
        # P&L is not a realized fill. Taxes/fees/slippage not claimed here.
        gross_pnl = round((price - cost) * shares, 2) if price is not None else None
        pnl_pct = round((price / cost - 1) * 100, 3) if price is not None else None
        remaining_risk = (round(max(0.0, price - stop) * shares, 2)
                          if price is not None and stop is not None else None)
        if remaining_risk is None:
            full_risk = False
        else:
            risk_sum += remaining_risk
        breached = price is not None and stop is not None and price <= stop
        rows.append({
            "股票": symbol, "現價": price, "方向": "既有持股（多方）",
            "多方評分": None, "空方評分": None, "買進觸發": None,
            "最高接受價": None, "停損／失效": stop,
            "分類": "X" if breached else "HOLD",
            "現在動作": "停損" if breached else "等待",
            "股數": shares, "平均成本": cost, "未實現毛損益": gross_pnl,
            "未實現毛報酬率%": pnl_pct, "目前價至停損風險": remaining_risk,
            "來源成交時間Asia/Taipei": trade_time,
            "費稅後淨損益": None,
            "續抱條件": "有效成交價仍高於停損且所有資料與風控通過",
            "減碼條件": "風險或集中度超出限制時人工評估減碼",
            "退出條件": "有效成交價觸及或跌破已知停損",
        })
        if remaining_risk is not None and remaining_risk > 5_000:
            reasons.append("SINGLE_POSITION_RISK_EXCEEDED_" + symbol)
        if cost * shares > 100_000:
            reasons.append("POSITION_CAP_EXCEEDED_" + symbol)
    if full_risk and risk_sum > 15_000:
        reasons.append("PORTFOLIO_HEAT_EXCEEDED")
    if not missing and not invalid:
        if _number(account["daily_pnl"]) <= -10_000:
            reasons.append("DAILY_LOSS_LOCKDOWN")
        if _number(account["consecutive_losses"]) >= 2:
            reasons.append("TWO_CONSECUTIVE_STOPS")
        if _number(account["concurrent_positions"]) > 3:
            reasons.append("MAX_CONCURRENT_POSITIONS")
        if _number(account["open_risk"]) > 15_000:
            reasons.append("OPEN_RISK_CAP_EXCEEDED")
    return {
        "schema": UPDATE_PRESENTATION, "status": "HOLD" if reasons else "RESEARCH_OBSERVATION_ONLY",
        "columns": MOBILE_COLUMNS, "rows": rows,
        "account_context_required": ACCOUNT_FIELDS,
        "missing_account_fields": missing, "invalid_account_fields": invalid,
        "risk_total_twd": round(risk_sum, 2) if full_risk and rows else None,
        "risk_certified": False, "new_entry_allowed": False,
        "portfolio_allowed": False, "reasons": list(dict.fromkeys(reasons)),
        "provider": "Fugle authorized individual quote required externally",
        "net_pnl_requires_verified_fees_and_fills": True,
        "action": "禁止交易" if reasons else "觀察",
        "manual_only": True, "broker_connected": False, "automatic_orders": False,
        "production_eligible": False,
    }
