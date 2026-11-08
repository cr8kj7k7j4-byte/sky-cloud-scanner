"""Synthetic diagnostic fixtures. No real historical returns or fill claims."""
import unittest
from comparison import compare_cost_stress, evaluate_trades


def trade(id='f1', strategy='A', exit_price=51.0):
    return dict(decision_id=id, strategy_id=strategy, symbol='1101',
                decision_at='2026-11-09T09:15:00+08:00',
                last_trade_at='2026-11-09T09:14:59+08:00',
                last_feature_at='2026-11-08T18:00:00+08:00',
                entry_price=50.0, stop_price=49.0, position_shares=1000,
                gross_capital=50000.0, open_risk=1000.0,
                direction='LONG', cost_rate=0.0045, source='SYNTHETIC_TEST',
                exit_price=exit_price, exit_at='2026-11-10T13:30:00+08:00',
                execution_evidence='SIMULATED', outcome_source='SYNTHETIC_TEST')


class ComparisonTest(unittest.TestCase):
    def test_cost_applied_to_r(self):
        o=evaluate_trades([trade()])['A']
        self.assertAlmostEqual(o['net_expectancy_r'], 0.775)

    def test_stress_cost_worse(self):
        s=compare_cost_stress([trade()])
        self.assertLess(s['stress']['A']['net_expectancy_r'],
                        s['primary']['A']['net_expectancy_r'])

    def test_reject_zero_cost_validation(self):
        with self.assertRaisesRegex(ValueError, 'invalid_cost'):
            evaluate_trades([trade()], -0.1)

    def test_reject_noncausal_exit(self):
        t=trade();t['exit_at']=t['decision_at']
        with self.assertRaisesRegex(ValueError, 'noncausal_exit'):
            evaluate_trades([t])

    def test_reject_actual_fill_claim(self):
        t=trade();t['execution_evidence']='ACTUAL'
        with self.assertRaisesRegex(ValueError, 'simulation_only'):
            evaluate_trades([t])

    def test_missing_outcome_source(self):
        t=trade();del t['outcome_source']
        with self.assertRaisesRegex(ValueError, 'missing_outcome_source'):
            evaluate_trades([t])

    def test_duplicate_decision(self):
        with self.assertRaisesRegex(ValueError, 'duplicate_decision_id'):
            evaluate_trades([trade(),trade()])

    def test_nonfinite_exit(self):
        t=trade();t['exit_price']=float('nan')
        with self.assertRaisesRegex(ValueError, 'invalid_exit_price'):
            evaluate_trades([t])

    def test_empty(self):
        with self.assertRaisesRegex(ValueError, 'missing_trades'):
            evaluate_trades([])

    def test_loss_and_profit_factor(self):
        x=evaluate_trades([trade('f1',exit_price=51.0),trade('f2',exit_price=49.0)])['A']
        self.assertEqual(x['sample_count'],2)
        self.assertLess(x['net_expectancy_r'], 0)
        self.assertGreater(x['profit_factor'],0)
        self.assertLess(x['profit_factor'],1)

    def test_keep_portfolio_unvalidated(self):
        x=evaluate_trades([trade()])['A']
        self.assertFalse(x['portfolio_validated'])
        self.assertIsNone(x['portfolio_max_drawdown'])
        self.assertEqual(x['status'],'INSUFFICIENT_DATA')


if __name__ == '__main__':
    unittest.main()
