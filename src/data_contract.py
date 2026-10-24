from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

@dataclass(frozen=True)
class FieldContract:
    name: str
    semantic_type: str
    unit: str
    nullable: bool
    source: str
    notes: str = ""

REGISTRY: Dict[str, FieldContract] = {
    "price": FieldContract("price", "float", "TWD/share", False, "market_data"),
    "open": FieldContract("open", "float", "TWD/share", False, "Fugle"),
    "high": FieldContract("high", "float", "TWD/share", False, "Fugle"),
    "low": FieldContract("low", "float", "TWD/share", False, "Fugle"),
    "close": FieldContract("close", "float", "TWD/share", False, "Fugle"),
    "volume_5m": FieldContract(
        "volume_5m", "float", "lot",
        False, "Fugle historical candles",
        "For standard board-lot equities, one lot = 1000 shares."
    ),
    "volume_shares": FieldContract(
        "volume_shares", "float", "share",
        False, "derived",
        "volume_5m * 1000 for standard board-lot equities."
    ),
    "turnover": FieldContract("turnover", "float", "TWD", False, "derived"),
    "return_pct": FieldContract("return_pct", "float", "percent", True, "derived"),
    "spread_pct": FieldContract("spread_pct", "float", "percent", True, "derived"),
    "timestamp": FieldContract(
        "timestamp", "datetime", "Asia/Taipei", False, "source",
        "All production timestamps must be timezone-aware or explicitly normalized."
    ),
    "vwap": FieldContract(
        "vwap", "float", "TWD/share", True, "derived",
        "Must retain calculation window and volume unit metadata."
    ),
    "eps": FieldContract("eps", "float", "TWD/share", True, "financial"),
    "revenue": FieldContract("revenue", "float", "TWD", True, "financial"),
    "foreign_holding_pct": FieldContract("foreign_holding_pct", "float", "percent", True, "official"),
}

def registry_snapshot() -> Dict[str, Dict[str, Any]]:
    return {k: asdict(v) for k, v in REGISTRY.items()}

def fugle_lots_to_shares(volume_lots: float) -> float:
    if volume_lots is None:
        raise ValueError("volume_lots cannot be None")
    if volume_lots < 0:
        raise ValueError("volume_lots cannot be negative")
    return float(volume_lots) * 1000.0

def candle_turnover_twd(close_twd: float, volume_lots: float) -> float:
    if close_twd is None or close_twd <= 0:
        raise ValueError("close_twd must be > 0")
    return float(close_twd) * fugle_lots_to_shares(float(volume_lots))

def validate_fugle_candle(candle: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for k in ("open", "high", "low", "close", "volume"):
        if candle.get(k) is None:
            errors.append(f"missing:{k}")
    if errors:
        return errors

    try:
        o, h, l, c = [float(candle[k]) for k in ("open", "high", "low", "close")]
        v = float(candle["volume"])
    except Exception:
        return ["type_error:numeric_fields"]

    if min(o, h, l, c) <= 0:
        errors.append("price_nonpositive")
    if h < max(o, l, c):
        errors.append("high_inconsistent")
    if l > min(o, h, c):
        errors.append("low_inconsistent")
    if v < 0:
        errors.append("volume_negative")

    turnover = candle_turnover_twd(c, max(v, 0.0))
    if turnover < 0:
        errors.append("turnover_negative")
    return errors

def validate_fugle_series(candles: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(candles)
    row_errors = []
    for i, row in enumerate(rows):
        errs = validate_fugle_candle(row)
        if errs:
            row_errors.append({"index": i, "errors": errs})

    turnovers = []
    for row in rows:
        try:
            turnovers.append(candle_turnover_twd(float(row["close"]), float(row["volume"])))
        except Exception:
            pass

    return {
        "rows": len(rows),
        "valid_rows": len(rows) - len(row_errors),
        "invalid_rows": len(row_errors),
        "errors": row_errors[:100],
        "turnover_min_twd": min(turnovers) if turnovers else None,
        "turnover_max_twd": max(turnovers) if turnovers else None,
        "contract_version": "P0-DATA-1.0",
    }
