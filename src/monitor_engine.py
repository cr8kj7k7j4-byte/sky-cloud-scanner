from dataclasses import dataclass, asdict
from pathlib import Path
import json

from .position_manager import evaluate_position


STATE_ZH = {
    "WATCH": "觀察",
    "NEAR_TRIGGER": "接近觸發",
    "TRIGGERED": "已觸發",
    "HOLDING": "續抱",
    "ADD_READY": "加碼條件成立",
    "EXIT": "退出",
    "DATA_REQUIRED": "資料不足",
    "NEAR_TARGET": "接近停利",
    "NEAR_STOP": "接近停損",
    "TAKE_PROFIT": "停利",
    "STOP": "停損",
    "INVALIDATED": "交易假設失效",
    "BLOCKED": "禁止交易",
    "DATA_INSUFFICIENT": "資料不足",
}


@dataclass
class MonitorDecision:
    symbol: str
    state: str
    action: str
    reason: str
    last: float | None = None
    trigger: float | None = None
    max_entry: float | None = None
    stop: float | None = None
    target: float | None = None
    previous_state: str | None = None
    changed: bool = False

    def to_dict(self):
        out = asdict(self)
        out["state_zh"] = STATE_ZH.get(self.state, self.state)
        return out


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _near(current, level, pct):
    if current is None or level is None or level == 0:
        return False
    return abs(current - level) / abs(level) <= pct


def evaluate_monitor_state(candidate, previous_state=None, near_pct=0.006):
    """
    P0-A MVP state machine.

    Long-side priority:
    1) hard rejection / risk block
    2) in-position stop / target / holding management
    3) max acceptable price (anti-chase)
    4) trigger / near-trigger
    5) watch

    This function never invents trigger/stop/target. Missing inputs remain WATCH
    or DATA_INSUFFICIENT rather than being converted into trade advice.
    """
    c = candidate or {}
    symbol = str(c.get("symbol") or "")
    last = _f(c.get("last", c.get("fugle_close")))
    trigger = _f(c.get("trigger"))
    max_entry = _f(c.get("max_entry", c.get("highest_acceptable_price")))
    stop = _f(c.get("stop"))
    target = _f(c.get("target", c.get("target1")))
    in_position = bool(c.get("in_position") or c.get("holding"))

    flags = [str(x) for x in c.get("flags", [])]
    x_flags = [x for x in flags if x.startswith("X:")]
    risk = c.get("risk") or {}
    risk_status = risk.get("status")

    state = "WATCH"
    action = "觀察"
    reason = "尚未符合新的盤中觸發條件"

    if last is None:
        state, action, reason = "DATA_INSUFFICIENT", "觀察", "缺少最新有效價格"
    elif x_flags:
        state, action, reason = "BLOCKED", "禁止交易", "；".join(x_flags)
    elif risk_status == "BLOCK":
        state, action = "BLOCKED", "禁止交易"
        reason = "；".join(risk.get("reasons", [])) or "P0-R 風控禁止進場"
    elif in_position:
        position = evaluate_position(c, near_pct=near_pct)
        state = position.state
        action = position.action
        reason = position.reason
        stop = position.effective_stop
        target = position.target
    else:
        if max_entry is not None and last > max_entry:
            state, action, reason = "INVALIDATED", "禁止交易", "已高於最高可接受買價，禁止追高"
        elif trigger is None:
            state, action, reason = "WATCH", "觀察", "尚未建立可驗證觸發價"
        elif last >= trigger:
            if risk_status == "RISK_INPUT_REQUIRED":
                state, action, reason = (
                    "DATA_INSUFFICIENT",
                    "等待",
                    "價格已到觸發區，但正式風控輸入不足",
                )
            elif risk_status not in (None, "ALLOW"):
                state, action, reason = "BLOCKED", "禁止交易", "P0-R 尚未允許進場"
            else:
                state, action, reason = "TRIGGERED", "等待", "價格已達觸發價，仍需確認量價/VWAP/結構"
        elif _near(last, trigger, near_pct):
            state, action, reason = "NEAR_TRIGGER", "等待", "價格接近觸發價"
        else:
            state, action, reason = "WATCH", "觀察", "尚未接近觸發價"

    return MonitorDecision(
        symbol=symbol,
        state=state,
        action=action,
        reason=reason,
        last=last,
        trigger=trigger,
        max_entry=max_entry,
        stop=stop,
        target=target,
        previous_state=previous_state,
        changed=previous_state is not None and previous_state != state,
    )


def load_state(path):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(path, decisions):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {d.symbol: d.state for d in decisions if d.symbol}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
