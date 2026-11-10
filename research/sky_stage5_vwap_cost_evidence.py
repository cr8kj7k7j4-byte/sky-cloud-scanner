"""Stage 5 read-only VWAP / execution-cost source diagnostic.

Use *observed* Fugle quote fields, never claim official VWAP or entry eligibility.
No provider requests, broker connections, orders, or promotion.
"""
from __future__ import annotations

import math

from src.cost_profiles import USER_CASH_DAYTRADE_20261022


def _positive(value):
    if isinstance(value, bool):
        return None
    try:
        v = float(value)
        return v if math.isfinite(v) and v > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def review_quote_vwap_evidence(microstructure):
    """Audit quote avgPrice against volume/turnover without certifying units.

    A quote's avgPrice is the provider's observed daily mean. No K-line
    causality or denominator-unit contract is asserted by this consistency test.
    """
    q = microstructure if isinstance(microstructure, dict) else {}
    avg = _positive(q.get("average_price"))
    turn = _positive(q.get("total_trade_value_twd"))
    volume_raw = _positive(q.get("total_trade_volume_raw"))
    implied = (turn / (volume_raw * avg)) if all(
        v is not None for v in (avg, turn, volume_raw)
    ) else None
    # Diagnostic dimensionless scale is *observed*, not an official unit
    # certification. Exact scale can change with security type or provider.
    plausible = (implied is not None and 980 <= implied <= 1020)
    if not all(x is not None for x in (avg, turn, volume_raw)):
        state = "INCOMPLETE_PROVIDER_AVERAGE_OR_TURNOVER"
    elif not plausible:
        state = "TURNOVER_VOLUME_AVERAGE_INCONSISTENT"
    else:
        state = "OBSERVATION_RECONCILED_NOT_VWAP_CERTIFIED"
    return {
        "source": "FUGLE_INTRADAY_QUOTE_AVGPRICE_TOTAL",
        "status": state,
        "provider_avg_price": avg,
        "provider_trade_value_twd": turn,
        "provider_trade_volume_raw": volume_raw,
        "turnover_to_volume_avg_implied_scale": round(implied, 5) if implied is not None else None,
        "volume_scale_1000_empirically_consistent": plausible,
        "official_volume_unit_contract_certified": False,
        "completed_five_minute_bar_causality_certified": False,
        "independent_intraday_vwap_recalculation_certified": False,
        "vwap_certified": False,
        "price_vs_provider_average_pct": None,
        "production_eligible": False,
    }


def review_cost_evidence():
    """Base fees are calibrated. Absence of fills/slippage is never 0 bps."""
    p = USER_CASH_DAYTRADE_20261022
    return {
        "source": "USER_OBSERVED_CALIBRATION_NOT_BROKER_CONTRACT",
        "profile_id": p.profile_id,
        "buy_fee_rate": p.buy_commission_rate,
        "sell_fee_rate": p.sell_commission_rate,
        "sell_tax_rate": p.sell_tax_rate,
        "base_round_trip_cost_pct": round(
            100 * (p.buy_commission_rate + p.sell_commission_rate + p.sell_tax_rate), 4
        ),
        "entry_slippage_bps": None,
        "exit_slippage_bps": None,
        "spread_execution_cost_bps": None,
        "fill_probability": None,
        "liquidity_impact_bps": None,
        "execution_cost_complete": False,
        "after_cost_rr_certified": False,
        "production_eligible": False,
    }
