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
    if item.get("candidate_scope") == "PARTIAL_SAMPLE_OBSERVATION":
        return None, None

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
    if item.get("candidate_scope") == "PARTIAL_SAMPLE_OBSERVATION":
        return "X"
    if item.get("execution_status") == "OPEN_ENTRY_PASSED_NO_CHASE":
        return "X"
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
    if item.get("candidate_scope") == "PARTIAL_SAMPLE_OBSERVATION":
        last = item.get("fugle_close") if item.get("data_status") == "VERIFIED_EXECUTED_TRADE" else None
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

    if item.get("candidate_scope") == "PARTIAL_SAMPLE_OBSERVATION":
        max_entry = None
        stop_text = "—"
    max_entry_text = _price(max_entry)
    cls = classification(item)
    action = action_text(item)
    trigger_text = buy_trigger_text(item)
    if item.get("candidate_scope") == "PARTIAL_SAMPLE_OBSERVATION":
        trigger_text = "未驗證／禁止新進場"

    return {
        "股票": stock,
        "現價": _bold(_price(last)),
        "方向": _bold(direction_label(bull, bear, item)),
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


def render_manual_position_report(
    message: str, *, quotes: dict | None = None,
    account_context: dict | None = None, now=None,
) -> dict:
    """Offline position-review to mobile-table adapter, never a network/ChatGPT trigger.

    Invoke the EXISTING manual reviewer first: scanner candidate rows must never
    replace the reviewer's not-applicable fields, A2 gate, or P0-R rejects.
    The caller must separately authenticate any injected Fugle A2 evidence.
    No storage, broker credentials, paid API, automation, or order execution.
    """
    from .sky_manual_position_review import review_manual_positions

    reviewed = review_manual_positions(
        message, quotes=quotes, account_context=account_context, now=now
    )
    rows = []
    for source in reviewed["rows"]:
        if source.get("交易方式") not in {"MARGIN_FINANCING", "CASH", "UNSPECIFIED"}:
            raise ValueError("INVALID_POSITION_REVIEW_ROW")
        if source.get("買進觸發") != "不適用（既有持股）" or source.get("最高接受價") != "不適用（既有持股）":
            raise ValueError("POSITION_ENTRY_NOT_APPLICABLE_CONTRACT")
        rows.append({
            "股票": str(source["股票"]),
            "現價": _price(source.get("現價")),
            "方向": source.get("方向") or "既有持股（多方）",
            "多方評分": "—" if source.get("多方評分") is None else str(source["多方評分"]),
            "空方評分": "—" if source.get("空方評分") is None else str(source["空方評分"]),
            "買進觸發": source["買進觸發"],
            "最高接受價": source["最高接受價"],
            "停損／失效": (
                _price(source["停損／失效"]) if source.get("停損／失效") is not None
                else "未設定（缺使用者停損）"
            ),
            "分類": "HOLD" if reviewed["status"] == "HOLD" else str(source.get("分類") or "HOLD"),
            "現在動作": (
                "停損" if source.get("現在動作") == "停損" and source.get("停損／失效") is not None
                else "等待"
            ),
            "欄位缺失原因": source.get("欄位缺失原因") or {},
        })
    header = "| " + " | ".join(COLUMNS) + " |"
    separator = "| " + " | ".join("---" for _ in COLUMNS) + " |"
    display = [header, separator]
    for row in rows:
        display.append("| " + " | ".join(
            str(row[c]).replace("|", "／").replace("\\n", " ") for c in COLUMNS
        ) + " |")
    if not rows:
        display.append("| 缺合格持股輸入 | — | — | — | — | — | — | — | HOLD | 等待 |")
    display.append("")
    display.append("此為既有持股觀察，並非新買進建議；缺有效 A2／停損／帳戶資料時維持 HOLD／NO_TRADE。")
    for row in rows:
        for field, reason in row["欄位缺失原因"].items():
            display.append(f"- {row['股票']} {field}：{str(reason).replace(chr(10), ' ')}")
    return {
        "schema": "SKY_MANUAL_POSITION_MOBILE_READBACK_V1",
        "status": reviewed["status"],
        "action": reviewed["action"],
        "rows": rows,
        "markdown": "\\n".join(display),
        "source_review": reviewed,
        "live_a2_certified": all(row.get("現價") != "—" for row in rows) and bool(rows),
        "new_entry_allowed": False,
        "automatic_orders": False,
        "production_eligible": False,
        "mobile_e2e_verified": False,
        "github_run_id": None,
        "artifact_id": None,
    }
