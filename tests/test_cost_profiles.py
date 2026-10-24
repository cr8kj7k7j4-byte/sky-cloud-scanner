from src.cost_profiles import (
    USER_CASH_DAYTRADE_20261022,
    USER_MARGIN_FINANCING_20261021,
    get_observed_cost_profile,
)


def test_cash_daytrade_profile_matches_observed_statement():
    p = USER_CASH_DAYTRADE_20261022
    assert p.sell_tax_rate == 0.0015
    assert round(p.buy_commission_rate, 6) == 0.000333
    assert p.transaction_mode == "CASH_DAYTRADE"


def test_margin_profile_keeps_interest_separate():
    p = USER_MARGIN_FINANCING_20261021
    assert p.sell_tax_rate == 0.003
    assert p.observed_financing_interest_twd is None
    assert p.financing_interest_mode == "PER_TRADE_OR_HOLDING_PERIOD_INPUT_REQUIRED"
    policy = p.to_execution_policy()
    assert policy.require_financing_interest is True
    assert policy.financing_interest_per_share is None


def test_profile_to_execution_policy_does_not_invent_market_friction():
    p = USER_CASH_DAYTRADE_20261022.to_execution_policy()
    assert p.buy_commission_rate == 0.000333
    assert p.sell_tax_rate == 0.0015
    assert p.entry_slippage_bps is None
    assert p.spread_bps is None


def test_unknown_profile_returns_none():
    assert get_observed_cost_profile("NOPE") is None
