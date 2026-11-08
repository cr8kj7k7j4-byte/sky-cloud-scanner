"""Deterministic fixtures: these are NOT actual price observations or P&L."""
import unittest
from research_gate import validate_signal


def case():
    return dict(decision_id='test-001', strategy_id='A', symbol='1101',
                decision_at='2026-11-09T09:15:00+08:00',
                last_trade_at='2026-11-09T09:14:59+08:00',
                last_feature_at='2026-11-08T18:00:00+08:00',
                entry_price=50.0, stop_price=49.0, position_shares=1000,
                gross_capital=50000.0, open_risk=1000.0,
                direction='LONG', cost_rate=0.0045, source='FIXTURE_ONLY')


class ResearchGateTest(unittest.TestCase):
    def test_valid_fixture(self):
        self.assertEqual(validate_signal(case())['strategy_id'], 'A')

    def test_missing_fields(self):
        r = case(); del r['source']
        with self.assertRaisesRegex(ValueError, 'missing'):
            validate_signal(r)

    def test_future_feature(self):
        r = case(); r['last_feature_at'] = '2026-11-09T10:00:00+08:00'
        with self.assertRaisesRegex(ValueError, 'future_feature'):
            validate_signal(r)

    def test_future_trade(self):
        r = case(); r['last_trade_at'] = '2026-11-09T10:00:00+08:00'
        with self.assertRaisesRegex(ValueError, 'future_market'):
            validate_signal(r)

    def test_timezone_missing(self):
        r = case(); r['decision_at'] = '2026-11-09T09:15:00'
        with self.assertRaisesRegex(ValueError, 'timezone_required'):
            validate_signal(r)

    def test_duplicate(self):
        ids=set(); validate_signal(case(), ids)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_signal(case(), ids)

    def test_price_limit(self):
        r=case(); r['entry_price']=100.0; r['gross_capital']=100000.0
        with self.assertRaisesRegex(ValueError, 'invalid_price'):
            validate_signal(r)

    def test_risk_limit(self):
        r=case(); r['open_risk']=6000.0
        with self.assertRaisesRegex(ValueError, 'trade_risk'):
            validate_signal(r)

    def test_capital_limit(self):
        r=case(); r['position_shares']=2200; r['gross_capital']=110000.0; r['open_risk']=2200.0
        with self.assertRaisesRegex(ValueError, 'capital_limit'):
            validate_signal(r)

    def test_three_positions(self):
        r=case(); r['positions_after_entry']=4
        with self.assertRaisesRegex(ValueError, 'max_three'):
            validate_signal(r)

    def test_portfolio_risk(self):
        r=case(); r['portfolio_risk_after_entry']=16000
        with self.assertRaisesRegex(ValueError, 'portfolio_risk'):
            validate_signal(r)

    def test_long_only(self):
        r=case(); r['direction']='SHORT'
        with self.assertRaisesRegex(ValueError, 'long_only'):
            validate_signal(r)

    def test_invalid_cost(self):
        r=case(); r['cost_rate']=-0.1
        with self.assertRaisesRegex(ValueError, 'invalid_cost'):
            validate_signal(r)

    def test_unregistered_strategy(self):
        r=case(); r['strategy_id']='X'
        with self.assertRaisesRegex(ValueError, 'strategy_not_registered'):
            validate_signal(r)


if __name__ == '__main__':
    unittest.main()
