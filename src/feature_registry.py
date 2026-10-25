from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

FEATURE_REGISTRY_VERSION = "1.0.0"

@dataclass(frozen=True)
class FeatureContract:
    name: str
    version: str
    description: str
    formula: str
    unit: str
    source: str
    lookback: str
    timestamp_semantics: str
    missing_policy: str
    leakage_risk: str
    production_status: str = "ACTIVE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

FEATURE_REGISTRY: Dict[str, FeatureContract] = {
    "momentum_1": FeatureContract(
        name="momentum_1", version="1.0.0",
        description="最近一根 5 分K收盤相對前一根收盤報酬",
        formula="(close_t / close_t-1 - 1) * 100",
        unit="percent", source="Fugle 5m candles",
        lookback="1 bar",
        timestamp_semantics="Only completed bars at or before feature as_of",
        missing_policy="NULL if fewer than 2 valid closes",
        leakage_risk="LOW if only completed bars are supplied",
    ),
    "momentum_5": FeatureContract(
        name="momentum_5", version="1.0.0",
        description="最近收盤相對五根前收盤報酬",
        formula="(close_t / close_t-5 - 1) * 100",
        unit="percent", source="Fugle 5m candles",
        lookback="5 bars",
        timestamp_semantics="Only completed bars at or before feature as_of",
        missing_policy="NULL if fewer than 6 valid closes",
        leakage_risk="LOW if only completed bars are supplied",
    ),
    "volume_ratio": FeatureContract(
        name="volume_ratio", version="1.0.0",
        description="最新 5 分K成交量相對先前樣本平均成交量",
        formula="volume_t / mean(volume_before_t)",
        unit="ratio", source="Fugle 5m candles",
        lookback="all supplied prior bars",
        timestamp_semantics="Current completed bar volume divided by prior completed bars",
        missing_policy="NULL if insufficient history or denominator <= 0",
        leakage_risk="MEDIUM if in-progress bar volume is supplied",
    ),
    "vwap_distance_pct": FeatureContract(
        name="vwap_distance_pct", version="1.0.0",
        description="最新價格相對來源 avg_price/VWAP 的乖離",
        formula="(last / avg_price - 1) * 100",
        unit="percent", source="quote.avg_price + market last",
        lookback="source-defined intraday VWAP window",
        timestamp_semantics="Both last and avg_price must be observable at feature as_of",
        missing_policy="NULL when avg_price unavailable or zero",
        leakage_risk="MEDIUM; source VWAP window must not include future trades",
    ),
    "intraday_range_pct": FeatureContract(
        name="intraday_range_pct", version="1.0.0",
        description="當日高低區間相對最新價格",
        formula="(day_high - day_low) / last * 100",
        unit="percent", source="intraday quote",
        lookback="session-to-as_of",
        timestamp_semantics="High/low must be known at feature as_of",
        missing_policy="NULL when high/low/last unavailable",
        leakage_risk="LOW if session high/low are point-in-time",
    ),
    "volatility_5": FeatureContract(
        name="volatility_5", version="1.0.0",
        description="最近五段 5 分K報酬母體標準差",
        formula="pstdev(close_i / close_i-1 - 1) * 100 over latest 5 returns",
        unit="percent", source="Fugle 5m candles",
        lookback="5 returns / 6 closes",
        timestamp_semantics="Only completed bars at or before feature as_of",
        missing_policy="NULL if insufficient valid closes",
        leakage_risk="LOW if only completed bars are supplied",
    ),
    "relative_strength": FeatureContract(
        name="relative_strength", version="1.0.0",
        description="個股當日漲跌幅減市場基準報酬",
        formula="stock_change_pct - market_return_pct",
        unit="percentage_points", source="market quote + P0-M market snapshot",
        lookback="session-to-as_of",
        timestamp_semantics="Stock and market inputs must share the same as_of boundary",
        missing_policy="NULL when either side is unavailable",
        leakage_risk="MEDIUM if stock and market timestamps are misaligned",
    ),
}

def registry_snapshot() -> Dict[str, Dict[str, Any]]:
    return {k: v.to_dict() for k, v in FEATURE_REGISTRY.items()}

def validate_registry() -> dict:
    errors = []
    for key, c in FEATURE_REGISTRY.items():
        if key != c.name:
            errors.append(f"name_mismatch:{key}:{c.name}")
        for field in (
            "version","description","formula","unit","source","lookback",
            "timestamp_semantics","missing_policy","leakage_risk","production_status"
        ):
            if not str(getattr(c, field) or "").strip():
                errors.append(f"missing_metadata:{key}:{field}")
    return {
        "registry_version": FEATURE_REGISTRY_VERSION,
        "feature_count": len(FEATURE_REGISTRY),
        "valid": not errors,
        "errors": errors,
    }

def validate_feature_names(features: dict) -> dict:
    names = set((features or {}).keys())
    registered = set(FEATURE_REGISTRY)
    return {
        "registered": sorted(names & registered),
        "unregistered": sorted(names - registered),
        "missing_registered": sorted(registered - names),
        "all_names_registered": not (names - registered),
    }
