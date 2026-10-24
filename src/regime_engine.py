from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class RegimeResult:
    trend: str
    volatility: str
    label: str
    confidence: float

    def to_dict(self):
        return asdict(self)


def detect_regime(index_change_pct=None, breadth_pct=None, volatility_pct=None):
    vol = 0.0 if volatility_pct is None else float(volatility_pct)

    if index_change_pct is None or breadth_pct is None:
        volatility = "HIGH" if vol >= 2.0 else "MEDIUM" if vol >= 1.0 else "LOW"
        return RegimeResult(
            trend="UNKNOWN",
            volatility=volatility,
            label=f"UNKNOWN_{volatility}",
            confidence=0.0,
        )

    idx = float(index_change_pct)
    breadth = float(breadth_pct)

    if idx >= 0.8 and breadth >= 55:
        trend = "BULL"
    elif idx <= -0.8 and breadth <= 45:
        trend = "BEAR"
    else:
        trend = "RANGE"

    if vol >= 2.0:
        volatility = "HIGH"
    elif vol >= 1.0:
        volatility = "MEDIUM"
    else:
        volatility = "LOW"

    confidence = min(1.0, abs(idx) / 2.0 + abs(breadth - 50.0) / 50.0)
    return RegimeResult(
        trend=trend,
        volatility=volatility,
        label=f"{trend}_{volatility}",
        confidence=round(confidence, 3),
    )
