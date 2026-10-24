from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class RegimeResult:
    trend: str
    volatility: str
    label: str
    confidence: float

    def to_dict(self):
        return asdict(self)


def detect_regime(index_change_pct=0.0, breadth_pct=None, volatility_pct=None):
    idx = float(index_change_pct or 0.0)
    breadth = 50.0 if breadth_pct is None else float(breadth_pct)
    vol = 0.0 if volatility_pct is None else float(volatility_pct)

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
