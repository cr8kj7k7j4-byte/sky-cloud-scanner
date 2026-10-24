from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import json


@dataclass(frozen=True)
class ShadowSignal:
    signal_id: str
    symbol: str
    side: str
    strategy_version: str
    model_version: str | None
    feature_schema_version: str | None
    rule_config_version: str | None
    generated_at: str
    entry_price: float
    stop_price: float
    target_price: float
    quantity: int
    regime: str | None = None
    setup: str | None = None
    phase: str | None = None
    source_time: str | None = None

    def to_dict(self):
        return asdict(self)


def _parse_iso(value):
    return datetime.fromisoformat(value)


def evaluate_shadow_trade(
    signal,
    *,
    exit_time,
    exit_price,
    max_price,
    min_price,
    fees=0.0,
    tax=0.0,
    slippage=0.0,
    exit_reason="UNKNOWN",
):
    s = signal if isinstance(signal, ShadowSignal) else ShadowSignal(**signal)

    if s.side.upper() != "LONG":
        raise ValueError("Phase 9 V1 supports LONG shadow trades only")
    if s.quantity <= 0:
        raise ValueError("quantity must be positive")
    if not (s.stop_price < s.entry_price < s.target_price):
        raise ValueError("invalid long trade geometry")

    gross = (float(exit_price) - s.entry_price) * s.quantity
    total_cost = float(fees) + float(tax) + float(slippage)
    net = gross - total_cost

    initial_risk = (s.entry_price - s.stop_price) * s.quantity
    r_multiple = net / initial_risk if initial_risk > 0 else None

    mfe_amount = (float(max_price) - s.entry_price) * s.quantity
    mae_amount = (s.entry_price - float(min_price)) * s.quantity
    mfe_r = mfe_amount / initial_risk if initial_risk > 0 else None
    mae_r = mae_amount / initial_risk if initial_risk > 0 else None

    holding_minutes = (
        _parse_iso(exit_time) - _parse_iso(s.generated_at)
    ).total_seconds() / 60.0

    return {
        **s.to_dict(),
        "exit_time": exit_time,
        "exit_price": float(exit_price),
        "exit_reason": exit_reason,
        "max_price": float(max_price),
        "min_price": float(min_price),
        "gross_pnl": round(gross, 2),
        "total_cost": round(total_cost, 2),
        "net_pnl": round(net, 2),
        "initial_risk": round(initial_risk, 2),
        "r_multiple": round(r_multiple, 4) if r_multiple is not None else None,
        "mfe_amount": round(mfe_amount, 2),
        "mae_amount": round(mae_amount, 2),
        "mfe_r": round(mfe_r, 4) if mfe_r is not None else None,
        "mae_r": round(mae_r, 4) if mae_r is not None else None,
        "holding_minutes": round(holding_minutes, 2),
        "mode": "SHADOW_ONLY",
        "live_order_allowed": False,
    }


def append_shadow_result(path, result):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result, ensure_ascii=False) + "\n")
    return result
