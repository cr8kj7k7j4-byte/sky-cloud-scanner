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
from . import config
from .risk_engine import RiskPolicy

TPE = timezone(timedelta(hours=8))
POSITION_LINE = re.compile(
    r"^(?P<symbol>\d{4,6})\s+"
    r"(?:(?P<trade_type>融資|現股)\s+)?"
    r"(?P<quantity>\d+(?:,\d{3})*)\s*(?P<unit>股|張)\s+"
    r"(?:平均成本|成本|均價)\s*(?P<cost>\d+(?:\.\d+)?)"
    r"(?:\s+停損\s*(?P<stop>\d+(?:\.\d+)?))?\s*$"
)
ACCOUNT_FIELDS = (
    "account_equity", "daily_pnl", "open_risk",
    "concurrent_positions", "correlated_open_risk",
    "drawdown_pct", "consecutive_losses",
)
# Strict manual text evidence: screenshot observations are NOT Fugle A2 quotes.
# No broker credentials, loan inference, collateral reconstruction or API calls.
BROKER_FIELD = re.compile(
    r"^(?P<field>截圖市價|券商預估損益|券商預估報酬率|"
    r"融資餘額|融資自備款|融資維持率)\s*"
    r"(?P<value>[+-]?\d[\d,]*(?:\.\d+)?)(?P<percent>%?)$"
)
BROKER_FIELDS = {
    "截圖市價": "screenshot_price",
    "券商預估損益": "broker_estimated_pnl",
    "券商預估報酬率": "broker_estimated_return_pct",
    "融資餘額": "margin_loan_balance",
    "融資自備款": "margin_own_cash",
    "融資維持率": "margin_maintenance_ratio_pct",
}
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
    elif lines and lines[0].startswith("Sky 持股檢查 "):
        lines[0] = lines[0][len("Sky 持股檢查 "):].strip()
    errors = []
    positions = []
    seen = set()
    broker_evidence = {}
    if not lines:
        errors.append("MISSING_POSITIONS")
    for line in lines:
        extra = BROKER_FIELD.fullmatch(line)
        if extra is not None:
            key = BROKER_FIELDS[extra["field"]]
            number = _number(extra["value"].replace(",", ""))
            correct_percent = (extra["percent"] == "%") == key.endswith("_pct")
            if key in broker_evidence or number is None or not correct_percent:
                errors.append("INVALID_OR_DUPLICATE_BROKER_EVIDENCE")
                continue
            if key not in ("broker_estimated_pnl", "broker_estimated_return_pct") and number < 0:
                errors.append("INVALID_BROKER_EVIDENCE_VALUE")
                continue
            if key in ("screenshot_price", "margin_loan_balance", "margin_own_cash") and number <= 0:
                errors.append("INVALID_BROKER_EVIDENCE_VALUE")
                continue
            broker_evidence[key] = number
            continue
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
        positions.append({"symbol": symbol, "shares": shares, "average_cost": cost, "stop": stop,
                          "trade_type": ("MARGIN_FINANCING" if match["trade_type"] == "融資"
                                         else "CASH" if match["trade_type"] == "現股"
                                         else "UNSPECIFIED")})
    if len(positions) > 3:
        errors.append("MAX_POSITIONS_EXCEEDED")
    if broker_evidence and len(positions) != 1:
        errors.append("AMBIGUOUS_BROKER_EVIDENCE_SYMBOL")
    if broker_evidence and positions and any(
            k.startswith("margin_") for k in broker_evidence
    ) and positions[0]["trade_type"] != "MARGIN_FINANCING":
        errors.append("MARGIN_EVIDENCE_REQUIRES_FINANCING_POSITION")
    return {"status": "PASS_INPUT" if not errors else "HOLD_POSITION_INPUT",
            "positions": positions, "errors": errors,
            "broker_evidence": broker_evidence}


def _verified_quote(quote: Any, symbol: str, now: datetime) -> tuple[float | None, str | None]:
    """Never treat snapshot capture/lastUpdated as a real last executed trade."""
    if not isinstance(quote, dict) or quote.get("symbol") != symbol:
        return None, None
    # A live holding may cost >100 TWD or be ineligible for *new* daytrade.
    # The collector exposes separate actual lastTrade.price observation evidence.
    if (quote.get("source") != "Fugle MarketData API /intraday/quote"
            or quote.get("position_trade_observed") is not True
            or quote.get("status") not in (
                "REALTIME_QUOTE_VERIFIED", "PRICE_CAP_EXCEEDED",
                "DAY_TRADE_NOT_ELIGIBLE", "DISPOSITION_NO_NEW_ENTRY")):
        return None, None
    price = _number(quote.get("last_trade_price"))
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
    broker = parsed.get("broker_evidence", {})
    reasons = list(parsed["errors"])
    if missing:
        reasons.append("HOLD_MISSING_ACCOUNT_CONTEXT")
    if invalid:
        reasons.append("HOLD_INVALID_ACCOUNT_CONTEXT")
    # P0-R canonical policy/config is clamped to the user's hard risk ceilings.
    policy = RiskPolicy(
        risk_per_trade_pct=min(config.RISK_PER_TRADE_PCT, 0.01),
        daily_loss_limit_pct=min(config.DAILY_LOSS_LIMIT_PCT, 0.02),
        max_portfolio_heat_pct=min(config.MAX_PORTFOLIO_HEAT_PCT, 0.03),
        max_position_pct=min(config.MAX_POSITION_PCT, 0.20),
        max_concurrent_positions=min(config.MAX_CONCURRENT_POSITIONS, 3),
    )
    equity = _number(account.get("account_equity"))
    single_risk_limit = min(5000.0, equity * policy.risk_per_trade_pct) if equity and equity > 0 else 5000.0
    position_cost_limit = min(100000.0, equity * policy.max_position_pct) if equity and equity > 0 else 100000.0
    heat_limit = min(15000.0, equity * policy.max_portfolio_heat_pct) if equity and equity > 0 else 15000.0
    daily_limit = min(10000.0, equity * policy.daily_loss_limit_pct) if equity and equity > 0 else 10000.0
    risk_sum = 0.0
    full_risk = True
    for position in parsed["positions"]:
        symbol = position["symbol"]
        shares = position["shares"]
        cost = position["average_cost"]
        stop = position["stop"]
        trade_type = position["trade_type"]
        # Broker evidence and loan variables are independent from the P0-R
        # account inputs and from Fugle A2. Never infer financing cash or debt.
        if trade_type == "MARGIN_FINANCING":
            for key, reason in (
                ("margin_loan_balance", "HOLD_MARGIN_LOAN_BALANCE_"),
                ("margin_own_cash", "HOLD_MARGIN_OWN_CASH_"),
                ("margin_maintenance_ratio_pct", "HOLD_MARGIN_MAINTENANCE_RATIO_"),
            ):
                if broker.get(key) is None:
                    reasons.append(reason + symbol)
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
        # Screenshot is a manual, undated observation. Its arithmetic is NOT
        # the verified current quote, financing account return, or net P&L.
        screenshot_price = broker.get("screenshot_price") if len(parsed["positions"]) == 1 else None
        screenshot_gross = (
            round((screenshot_price - cost) * shares, 2)
            if screenshot_price is not None else None
        )
        broker_pnl = broker.get("broker_estimated_pnl") if len(parsed["positions"]) == 1 else None
        screenshot_to_broker_gap = (
            round(screenshot_gross - broker_pnl, 2)
            if screenshot_gross is not None and broker_pnl is not None else None
        )
        # Explain each unavailable cell without inventing a score, entry or exit.
        field_reasons = {
            "多方評分": "未執行符合條件的正式多方模型；持股損益不依賴新進場評分",
            "空方評分": "未執行符合條件的獨立空方模型；持股損益不依賴新進場評分",
            "買進觸發": "不適用：此為已持有部位，不是新買進訊號",
            "最高接受價": "不適用：此為已持有部位，不提供新買進價格",
            "目標價": "尚無經認證的持股退出策略目標，不可由成本或現價推算",
            "成本後RR": "已持有部位缺合格目標、完整成交成本與滑價；不計算新進場RR",
            "費稅後淨損益": "缺實際買賣費率與可驗證成交成本；僅顯示未實現毛損益",
        }
        if price is None:
            field_reasons["現價"] = (
                "缺同股 Fugle A2 Individual Quote 真實 lastTrade.price/time、"
                "交易日或120秒內成交認證；參考價/快照不可代替"
            )
            field_reasons["未實現毛損益"] = "缺已認證成交價；不以收盤/快照價計算"
        if stop is None:
            field_reasons["停損／失效"] = "使用者尚未提供真實持股停損價"
        if price is None or stop is None:
            field_reasons["目前價至停損風險"] = (
                "需同時提供已認證成交價與使用者停損價"
            )
        rows.append({
            "股票": symbol, "現價": price, "方向": "既有持股（多方）",
            "多方評分": None, "空方評分": None,
            "買進觸發": "不適用（既有持股）",
            "最高接受價": "不適用（既有持股）", "停損／失效": stop,
            "分類": "X" if breached else "HOLD",
            "現在動作": "停損" if breached else "等待",
            "欄位缺失原因": field_reasons,
            "買進觸發說明": "不適用（既有持股）",
            "最高接受價說明": "不適用（既有持股）",
            "目標價": None, "成本後RR": None,
            "交易方式": trade_type, "股數": shares, "平均成本": cost,
            "股票原始成交總額": round(cost * shares, 2),
            "融資自備款": (broker.get("margin_own_cash") if trade_type == "MARGIN_FINANCING" else None),
            "融資餘額": (broker.get("margin_loan_balance") if trade_type == "MARGIN_FINANCING" else None),
            "融資維持率%": (broker.get("margin_maintenance_ratio_pct") if trade_type == "MARGIN_FINANCING" else None),
            "券商截圖市價（未認證）": screenshot_price,
            "截圖價差毛損益（未扣費）": screenshot_gross,
            "券商預估損益（原值）": broker_pnl,
            "券商預估報酬率%（原值）": (
                broker.get("broker_estimated_return_pct") if len(parsed["positions"]) == 1 else None
            ),
            "截圖毛損益減券商預估損益（差額原因未認證）": screenshot_to_broker_gap,
            "券商截圖行情狀態": (
                "USER_PROVIDED_UNDATED_REFERENCE_NOT_A2"
                if screenshot_price is not None else "MISSING_SCREENSHOT_REFERENCE"
            ),
            "未實現毛損益": gross_pnl,
            "未實現毛報酬率%": pnl_pct, "目前價至停損風險": remaining_risk,
            "來源成交時間Asia/Taipei": trade_time,
            "費稅後淨損益": None,
            "續抱條件": "有效成交價仍高於停損且所有資料與風控通過",
            "減碼條件": "風險或集中度超出限制時人工評估減碼",
            "退出條件": "有效成交價觸及或跌破已知停損",
        })
        if trade_type == "MARGIN_FINANCING":
            if broker.get("margin_loan_balance") is None:
                field_reasons["融資餘額"] = "缺券商實際融資借款餘額，不能從成交總額反推"
            if broker.get("margin_own_cash") is None:
                field_reasons["融資自備款"] = "缺券商實際自備款，不以券商報酬率倒推"
            if broker.get("margin_maintenance_ratio_pct") is None:
                field_reasons["融資維持率%"] = "缺券商實際維持率／抵押品價值，不能用股價自行估算"
            field_reasons["券商預估報酬率%（原值）"] = (
                "融資報酬率分母及券商費用口徑未獨立認證；原值僅供對帳"
            )
            field_reasons["費稅後淨損益"] = (
                "融資費率、利息、實際融資餘額與券商估價口徑尚未完整認證"
            )
        if remaining_risk is not None and remaining_risk > single_risk_limit:
            reasons.append("SINGLE_POSITION_RISK_EXCEEDED_" + symbol)
        if cost * shares > position_cost_limit:
            reasons.append("POSITION_CAP_EXCEEDED_" + symbol)
    if full_risk and risk_sum > heat_limit:
        reasons.append("PORTFOLIO_HEAT_EXCEEDED")
    if not missing and not invalid:
        if _number(account["daily_pnl"]) <= -daily_limit:
            reasons.append("DAILY_LOSS_LOCKDOWN")
        if _number(account["consecutive_losses"]) >= 2:
            reasons.append("TWO_CONSECUTIVE_STOPS")
        if _number(account["concurrent_positions"]) > policy.max_concurrent_positions:
            reasons.append("MAX_CONCURRENT_POSITIONS")
        if _number(account["open_risk"]) > heat_limit:
            reasons.append("OPEN_RISK_CAP_EXCEEDED")
    return {
        "schema": UPDATE_PRESENTATION, "status": "HOLD" if reasons else "RESEARCH_OBSERVATION_ONLY",
        "columns": MOBILE_COLUMNS, "rows": rows,
        "account_context_required": ACCOUNT_FIELDS,
        "missing_account_fields": missing, "invalid_account_fields": invalid,
        "帳戶風控缺失原因": {
            field: "未提供真實帳戶資料（不得視為零）" for field in missing
        } | {field: "數值無效或不符合 P0-R 欄位規格" for field in invalid},
        "risk_total_twd": round(risk_sum, 2) if full_risk and rows else None,
        "broker_evidence_status": "USER_ENTERED_SCREENSHOT_UNVERIFIED",
        "broker_evidence": broker,
        "risk_certified": False, "new_entry_allowed": False,
        "p0r_policy": "EXISTING_RISK_POLICY_CLAMPED_TO_USER_CAPS",
        "portfolio_allowed": False, "reasons": list(dict.fromkeys(reasons)),
        "provider": "Fugle authorized individual quote required externally",
        "net_pnl_requires_verified_fees_and_fills": True,
        "action": "禁止交易" if reasons else "觀察",
        "manual_only": True, "broker_connected": False, "automatic_orders": False,
        "production_eligible": False,
    }
