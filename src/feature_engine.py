from dataclasses import dataclass, asdict
from statistics import mean, pstdev


@dataclass(frozen=True)
class FeatureSnapshot:
    momentum_1: float | None
    momentum_5: float | None
    volume_ratio: float | None
    vwap_distance_pct: float | None
    intraday_range_pct: float | None
    volatility_5: float | None
    relative_strength: float | None

    def to_dict(self):
        return asdict(self)


def _safe_pct(a, b):
    if a is None or b in (None, 0):
        return None
    return (float(a) / float(b) - 1.0) * 100.0


def build_features(candidate, candles=None, market_return_pct=None):
    candidate = candidate or {}
    candles = candles or []
    closes = [float(x["close"]) for x in candles if x.get("close") is not None]
    volumes = [float(x["volume"]) for x in candles if x.get("volume") is not None]

    last = candidate.get("fugle_close", candidate.get("last"))
    avg_price = candidate.get("avg_price")
    high = candidate.get("fugle_high")
    low = candidate.get("fugle_low")

    momentum_1 = None
    momentum_5 = None
    volatility_5 = None
    if len(closes) >= 2:
        momentum_1 = _safe_pct(closes[-1], closes[-2])
    if len(closes) >= 6:
        momentum_5 = _safe_pct(closes[-1], closes[-6])
        rets = []
        for i in range(len(closes) - 5, len(closes)):
            prev = closes[i - 1]
            if prev:
                rets.append(closes[i] / prev - 1.0)
        if rets:
            volatility_5 = pstdev(rets) * 100.0

    volume_ratio = None
    if len(volumes) >= 2:
        base = mean(volumes[:-1]) if volumes[:-1] else 0
        if base > 0:
            volume_ratio = volumes[-1] / base

    vwap_distance_pct = _safe_pct(last, avg_price)

    intraday_range_pct = None
    if high is not None and low is not None and last not in (None, 0):
        intraday_range_pct = (float(high) - float(low)) / float(last) * 100.0

    relative_strength = None
    cp = candidate.get("change_pct")
    if cp is not None and market_return_pct is not None:
        relative_strength = float(cp) - float(market_return_pct)

    return FeatureSnapshot(
        momentum_1=momentum_1,
        momentum_5=momentum_5,
        volume_ratio=volume_ratio,
        vwap_distance_pct=vwap_distance_pct,
        intraday_range_pct=intraday_range_pct,
        volatility_5=volatility_5,
        relative_strength=relative_strength,
    )
