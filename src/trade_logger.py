from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import json


@dataclass(frozen=True)
class TradeRecord:
    symbol: str
    side: str
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    quantity: int
    initial_stop: float
    fees: float = 0.0
    tax: float = 0.0
    slippage: float = 0.0
    max_price_during_trade: float | None = None
    min_price_during_trade: float | None = None
    setup: str | None = None
    phase: str | None = None
    model_version: str | None = None

    def to_dict(self):
        return asdict(self)


def _parse_iso(value):
    return datetime.fromisoformat(value)


def evaluate_trade_record(record):
    r = record if isinstance(record, TradeRecord) else TradeRecord(**record)

    if r.side.upper() not in {"LONG", "SHORT"}:
        raise ValueError("side must be LONG or SHORT")
    if r.quantity <= 0:
        raise ValueError("quantity must be positive")
    if r.entry_price <= 0 or r.exit_price <= 0 or r.initial_stop <= 0:
        raise ValueError("prices must be positive")

    direction = 1.0 if r.side.upper() == "LONG" else -1.0
    gross = (r.exit_price - r.entry_price) * direction * r.quantity
    total_cost = float(r.fees) + float(r.tax) + float(r.slippage)
    net = gross - total_cost

    initial_risk_per_share = abs(r.entry_price - r.initial_stop)
    initial_risk = initial_risk_per_share * r.quantity
    r_multiple = net / initial_risk if initial_risk > 0 else None

    mfe = None
    mae = None
    if r.max_price_during_trade is not None and r.min_price_during_trade is not None:
        if r.side.upper() == "LONG":
            mfe = (r.max_price_during_trade - r.entry_price) * r.quantity
            mae = (r.entry_price - r.min_price_during_trade) * r.quantity
        else:
            mfe = (r.entry_price - r.min_price_during_trade) * r.quantity
            mae = (r.max_price_during_trade - r.entry_price) * r.quantity

    duration_minutes = (
        _parse_iso(r.exit_time) - _parse_iso(r.entry_time)
    ).total_seconds() / 60.0

    return {
        **r.to_dict(),
        "gross_pnl": round(gross, 2),
        "total_cost": round(total_cost, 2),
        "net_pnl": round(net, 2),
        "initial_risk": round(initial_risk, 2),
        "r_multiple": round(r_multiple, 4) if r_multiple is not None else None,
        "mfe_amount": round(mfe, 2) if mfe is not None else None,
        "mae_amount": round(mae, 2) if mae is not None else None,
        "holding_minutes": round(duration_minutes, 2),
    }


def append_trade(path, record):
    evaluated = evaluate_trade_record(record)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(evaluated, ensure_ascii=False) + "\n")
    return evaluated
