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
    # Extreme but finite provider values can overflow the denominator or
    # ratio. Never serialize NaN/Infinity as a JSON evidence metric.
    implied = None
    if all(v is not None for v in (avg, turn, volume_raw)):
        denominator = volume_raw * avg
        if math.isfinite(denominator) and denominator > 0:
            ratio = turn / denominator
            if math.isfinite(ratio) and ratio > 0:
                implied = ratio
    # Diagnostic dimensionless scale is *observed*, not an official unit
    # certification. Exact scale can change with security type or provider.
    plausible = (implied is not None and 980 <= implied <= 1020)
    if not all(x is not None for x in (avg, turn, volume_raw)):
        state = "INCOMPLETE_PROVIDER_AVERAGE_OR_TURNOVER"
    elif implied is None or not plausible:
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


def review_independent_trades_vwap(pages, *, symbol, exchange, trade_date,
                                   quote_total_volume, observed_at):
    """Offline Fugle trades-page audit; never treats source documents as live proof.

    The official stock Intraday Trades API requires offset pagination until an
    empty page. In-session descending pages may shift as executions arrive.
    This audit only produces a research arithmetic cross-check. It cannot
    certify real provider origin, same-run independent readback, PIT, or VWAP.
    """
    from datetime import datetime, timezone
    from decimal import Decimal
    from zoneinfo import ZoneInfo

    result = {
        "schema": "SKY_FUGLE_TICK_VWAP_SOURCE_AUDIT_V1",
        "source": "FUGLE_INTRADAY_TRADES_EXISTING_RECEIPTS_ONLY",
        "status": "HOLD_INCOMPLETE_TRADES_SOURCE",
        "trade_count": 0,
        "page_count": 0,
        "observed_tick_volume": None,
        "quote_total_volume": quote_total_volume,
        "calculated_trade_vwap_research": None,
        "source_provenance_certified": False,
        "complete_page_chain_certified": False,
        "quote_cutoff_pit_certified": False,
        "independent_intraday_vwap_recalculation_certified": False,
        "vwap_certified": False,
        "production_eligible": False,
    }
    if (not isinstance(symbol, str) or not symbol.isascii() or not symbol.isdigit()
        or exchange not in ("TWSE", "TPEx") or not isinstance(trade_date, str)
        or not isinstance(observed_at, datetime) or observed_at.utcoffset() is None
        or isinstance(quote_total_volume, bool)
        or not isinstance(quote_total_volume, int) or quote_total_volume <= 0
        or not isinstance(pages, list) or not 2 <= len(pages) <= 100):
        return result

    tpe = ZoneInfo("Asia/Taipei")
    local_now = observed_at.astimezone(tpe)
    if local_now.date().isoformat() != trade_date:
        return result
    expected_offset = 0
    seen = set()
    volume = 0
    turnover = Decimal(0)
    terminal = False
    data_pages = 0
    for index, page in enumerate(pages):
        if not isinstance(page, dict) or type(page.get("offset")) is not int:
            return result
        limit = page.get("limit")
        payload = page.get("payload")
        if (type(limit) is not int or not 1 <= limit <= 500
            or page["offset"] != expected_offset or not isinstance(payload, dict)
            or payload.get("symbol") != symbol
            or payload.get("exchange") != exchange
            or payload.get("date") != trade_date
            or payload.get("type") != "EQUITY"
            or page.get("isTrial") is not False):
            return result
        rows = payload.get("data")
        if not isinstance(rows, list) or len(rows) > limit:
            return result
        if not rows:
            terminal = index == len(pages) - 1
            break
        data_pages += 1
        for row in rows:
            if not isinstance(row, dict):
                return result
            serial, micros = row.get("serial"), row.get("time")
            price, size = _positive(row.get("price")), _positive(row.get("size"))
            if (type(serial) is not int or type(micros) is not int
                or serial in seen or price is None or size is None
                or size != int(size)):
                return result
            try:
                trade_at = datetime.fromtimestamp(micros / 1_000_000, timezone.utc).astimezone(tpe)
            except (OverflowError, ValueError, OSError):
                return result
            if trade_at.date().isoformat() != trade_date or trade_at > local_now:
                return result
            # Documented special after-hours trade serial is not intraday
            # quote volume and must be omitted from a regular-session VWAP.
            if serial == 99999999 and trade_at.hour == 14 and trade_at.minute == 30:
                seen.add(serial)
                continue
            if not ((9 <= trade_at.hour < 13) or
                    (trade_at.hour == 13 and trade_at.minute <= 30)):
                return result
            seen.add(serial)
            volume += int(size)
            turnover += Decimal(str(price)) * Decimal(int(size))
        expected_offset += limit
    if not terminal or not data_pages or volume <= 0 or volume != quote_total_volume:
        return result
    candidate = turnover / Decimal(volume)
    if not candidate.is_finite() or candidate <= 0:
        return result
    result.update({
        "status": "TRADE_PAGES_RECONCILED_RESEARCH_ONLY",
        "trade_count": len(seen),
        "page_count": data_pages,
        "observed_tick_volume": volume,
        "calculated_trade_vwap_research": float(round(candidate, 6)),
        "complete_page_chain_certified": True,
        # A complete fixture or archive is not evidence that pages were
        # fetched atomically from Fugle or matched the point-in-time quote.
        "source_provenance_certified": False,
        "quote_cutoff_pit_certified": False,
        "independent_intraday_vwap_recalculation_certified": False,
        "vwap_certified": False,
    })
    return result


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
