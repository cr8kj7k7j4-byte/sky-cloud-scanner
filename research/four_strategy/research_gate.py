"""Research-only signal contract validator. No trading or performance claims."""
from datetime import datetime
from math import isfinite

ALLOWED = frozenset({'A', 'B', 'C', 'D'})
REQUIRED = frozenset({
    'decision_id', 'strategy_id', 'symbol', 'decision_at',
    'last_trade_at', 'last_feature_at', 'entry_price', 'stop_price',
    'position_shares', 'gross_capital', 'open_risk', 'direction',
    'cost_rate', 'source',
})


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp_not_string')
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid_timestamp') from exc
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError('timezone_required')
    return d


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError('invalid_' + field)
    return float(value)


def validate_signal(record, seen_ids=None):
    """Return validated record; fail closed if required evidence is missing.

    This is an input contract, NOT proof of historical validity or fills.
    """
    if not isinstance(record, dict):
        raise ValueError('record_not_object')
    missing = REQUIRED.difference(record)
    if missing:
        raise ValueError('missing:' + ','.join(sorted(missing)))
    ident = record['decision_id']
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError('invalid_decision_id')
    if seen_ids is not None and ident in seen_ids:
        raise ValueError('duplicate_decision_id')
    if record['strategy_id'] not in ALLOWED:
        raise ValueError('strategy_not_registered')
    if not isinstance(record['symbol'], str) or not record['symbol'].strip():
        raise ValueError('invalid_symbol')
    if not isinstance(record['source'], str) or not record['source'].strip():
        raise ValueError('missing_source')
    if record['direction'] != 'LONG':
        raise ValueError('long_only')
    decision = _timestamp(record['decision_at'])
    if _timestamp(record['last_trade_at']) > decision:
        raise ValueError('future_market_data')
    if _timestamp(record['last_feature_at']) > decision:
        raise ValueError('future_feature_data')
    price = _number(record['entry_price'], 'entry_price')
    stop = _number(record['stop_price'], 'stop_price')
    shares = record['position_shares']
    if isinstance(shares, bool) or not isinstance(shares, int) or shares <= 0:
        raise ValueError('invalid_position_shares')
    if not 0 < stop < price < 100:
        raise ValueError('invalid_price_or_stop')
    capital = _number(record['gross_capital'], 'gross_capital')
    risk = _number(record['open_risk'], 'open_risk')
    cost = _number(record['cost_rate'], 'cost_rate')
    if not 0 <= cost < 1:
        raise ValueError('invalid_cost_rate')
    if capital <= 0 or capital > 100000 or abs(capital - price * shares) > 0.01:
        raise ValueError('capital_limit_or_mismatch')
    if risk <= 0 or risk > 5000 or risk + 0.01 < (price - stop) * shares:
        raise ValueError('trade_risk_limit_or_mismatch')
    if 'positions_after_entry' in record:
        count = record['positions_after_entry']
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 3:
            raise ValueError('max_three_positions')
    if 'portfolio_risk_after_entry' in record:
        total = _number(record['portfolio_risk_after_entry'], 'portfolio_risk_after_entry')
        if total < risk or total > 15000:
            raise ValueError('portfolio_risk_limit')
    if seen_ids is not None:
        seen_ids.add(ident)
    return record
