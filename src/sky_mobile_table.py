from __future__ import annotations

from typing import Any


COLUMNS = [
    "股票", "現價", "方向", "多方評分", "空方評分",
    "買進觸發", "最高接受價", "停損／失效", "分類", "現在動作",
]


def _num(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _clamp(value, lo=0.0, hi=100.0):
    return max(lo, min(hi, value))


def _price(value):
    x = _num(value)
    if x is None:
        return "—"
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s


def _bold(text):
    if text in (None, ""):
        return "—"
    if text == "—":
        return "—"
    return f"**{text}**"


def evidence_scores(item: dict[str, Any]) -> tuple[int | None, int | None]:
    """Display-only bull/bear evidence scores.

    These are deterministic evidence-comparison scores, NOT probability,
    win rate, expected return, or a trading signal. They never feed P0-O,
    P0-C, P0-R, entry, stop, target, or promotion decisions.
    """
    item = item or {}

    explicit_bull = next(
        (_num(item.get(k)) for k in ("bull_score", "long_score", "bullish_score")
         if _num(item.get(k)) is not None),
        None,
    )
    explicit_bear = next(
        (_num(item.get(k)) for k in ("bear_score", "short_score", "bearish_score")
         if _num(item.get(k)) is not None),
        None,
    )
    if explicit_bull is not None or explicit_bear is not None:
        return (
            round(_clamp(explicit_bull)) if explicit_bull is not None else None,
            round(_clamp(explicit_bear)) if explicit_bear is not None else None,
        )

    last = _num(item.get("fugle_close", item.get("current_price", item.get("last"))))
    open_ = _num(item.get("open", item.get("entry_open")))
    change = _num(item.get("change_pct"))
    relative = _num(item.get("relative_to_market_pct", item.get("relative_strength")))
    high = _num(item.get("fugle_high", item.get("high")))
    low = _num(item.get("fugle_low", item.get("low")))

    # Require at least two observable price/context inputs before deriving a score.
    observed = sum(x is not None for x in (last, open_, change, relative, high, low))
    if observed < 2:
        return None, None

    impulse = 0.0
    if change is not None:
        impulse += _clamp(change * 3.0, -18.0, 18.0)
    if relative is not None:
        impulse += _clamp(relative * 4.0, -15.0, 15.0)
    if last is not None and open_ not in (None, 0):
        impulse += 10.0 if last >= open_ else -10.0
    if None not in (last, high, low) and high > low:
        loc = (last - low) / (high - low)
        if loc >= 0.70:
            impulse += 8.0
        elif loc <= 0.30:
            impulse -= 8.0

    # Frozen V1.1 cross-sectional evidence, when present.
    rs = _num(item.get("rs_pct"))
    breadth = _num(item.get("breadth"))
    if rs is not None:
        impulse += _clamp((rs - 0.5) * 30.0, -10.0, 15.0)
    if breadth is not None:
        impulse += _clamp((breadth - 0.5) * 30.0, -10.0, 10.0)

    bull = round(_clamp(50.0 + impulse))
    bear = round(_clamp(50.0 - impulse))
    return bull, bear


def direction_label(bull: int | None, bear: int | None, item: dict[str, Any]) -> str:
    explicit = item.get("direction")
    if explicit:
        return str(explicit)
    if bull is None or bear is None:
        return "觀察"
    diff = bull - bear
    if diff >= 30:
        return "偏多"
    if diff >= 10:
        return "中性偏多"
    if diff <= -30:
        return "偏空"
    if diff <= -10:
        return "中性偏空"
    return "中性"


def _plan(item):
    return item.get("strategy_plan") or {}


def _monitor(item):
    return item.get("monitor") or {}


def buy_trigger_text(item: dict[str, Any]) -> str:
    if item.get("execution_status") == "OPEN_ENTRY_PASSED_NO_CHASE":
        return f"原進場 D+1 開盤 {_price(item.get('entry_open'))}（已過，不追）"
    if item.get("entry_open") is not None and item.get("strategy") == "Sky Swing Challenger V1.1":
        return f"D+1 開盤 {_price(item.get('entry_open'))}"

    plan = _plan(item)
    trigger = (
        item.get("buy_trigger")
        or item.get("trigger")
        or plan.get("trigger")
        or _monitor(item).get("trigger")
    )
    if trigger is None:
        return str(item.get("trigger_text") or "無有效多方觸發")
    if isinstance(trigger, (int, float)):
        return _price(trigger)
    return str(trigger)


def classification(item: dict[str, Any]) -> str:
    decision = item.get("decision") or {}
    action = str(
        item.get("current_action")
        or item.get("candidate_action")
        or decision.get("action")
        or _monitor(item).get("action")
        or ""
    )
    flags = [str(x) for x in item.get("flags", [])]
    if decision.get("status") == "BLOCK" or action in {"禁止交易", "停損", "退出"} or any(x.startswith("X:") for x in flags):
        return "X"
    explicit = item.get("classification")
    if explicit in {"A+", "A", "X"}:
        return explicit
    cap = str(item.get("classification_cap") or "")
    if cap.startswith("A+"):
        return "A+"
    if cap.startswith("A"):
        return "A"
    # Live research/swing candidate without a hard rejection is observable A.
    if item.get("candidate_scope") or item.get("strategy_signal"):
        return "A"
    return "A"


def action_text(item: dict[str, Any]) -> str:
    if item.get("execution_status") == "OPEN_ENTRY_PASSED_NO_CHASE":
        return "禁止交易"
    decision = item.get("decision") or {}
    action = (
        item.get("current_action")
        or item.get("candidate_action")
        or decision.get("action")
        or _monitor(item).get("action")
        or "觀察"
    )
    allowed = {"買進", "等待", "觀察", "續抱", "加碼", "減碼", "停損", "退出", "禁止交易"}
    return action if action in allowed else "觀察"


def normalize_mobile_row(item: dict[str, Any]) -> dict[str, str]:
    item = item or {}
    bull, bear = evidence_scores(item)
    plan = _plan(item)
    monitor = _monitor(item)

    last = item.get("fugle_close", item.get("current_price", item.get("last")))
    max_entry = (
        item.get("highest_acceptable_price")
        or item.get("max_entry")
        or plan.get("max_entry")
        or monitor.get("max_entry")
    )
    stop = (
        item.get("stop")
        or item.get("initial_stop")
        or plan.get("stop")
        or monitor.get("stop")
    )
    invalidation = item.get("invalidation_text")
    if invalidation:
        stop_text = str(invalidation)
    elif stop is not None:
        stop_text = f"跌破 {_price(stop)}"
    else:
        stop_text = "—"

    name = str(item.get("name") or "").strip()
    symbol = str(item.get("symbol") or "").strip()
    stock = f"**{symbol} {name}**".strip() if (symbol or name) else "—"

    bull_text = _bold(f"{bull} / 100") if bull is not None else "—"
    bear_text = _bold(f"{bear} / 100") if bear is not None else "—"

    max_entry_text = _price(max_entry)
    cls = classification(item)
    action = action_text(item)
    trigger_text = buy_trigger_text(item)

    return {
        "股票": stock,
        "現價": _bold(_price(last)),
        "方向": direction_label(bull, bear, item),
        "多方評分": bull_text,
        "空方評分": bear_text,
        "買進觸發": _bold(trigger_text) if trigger_text != "—" else "—",
        "最高接受價": _bold(max_entry_text) if max_entry_text != "—" else "—",
        "停損／失效": _bold(stop_text) if stop_text != "—" else "—",
        "分類": _bold(cls),
        "現在動作": _bold(action),
    }


def render_mobile_table(items: list[dict[str, Any]]) -> str:
    rows = [normalize_mobile_row(x) for x in (items or [])]
    header = "| " + " | ".join(COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in COLUMNS) + " |"
    if not rows:
        return "\n".join([header, sep, "| 目前沒有符合條件的新進場標的 | — | — | — | — | — | — | — | X | 禁止交易 |"])
    body = [
        "| " + " | ".join(str(row[c]).replace("|", "／") for c in COLUMNS) + " |"
        for row in rows
    ]
    return "\n".join([header, sep, *body])
