"""P0-R: missing loss-streak evidence must never become a synthetic zero."""
import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class LossStreakSourceGuardTests(unittest.TestCase):
    def test_config_missing_history_is_unknown(self):
        with patch.dict(os.environ, {"CONSECUTIVE_LOSSES": ""}):
            cfg = runpy.run_path(str(ROOT / "src" / "config.py"))
        self.assertIsNone(cfg["CONSECUTIVE_LOSSES"])

    def test_config_explicit_history_remains_numeric(self):
        for raw, expected in (("0", 0), ("1", 1), ("2", 2)):
            with self.subTest(raw=raw):
                with patch.dict(os.environ, {"CONSECUTIVE_LOSSES": raw}):
                    cfg = runpy.run_path(str(ROOT / "src" / "config.py"))
                self.assertEqual(cfg["CONSECUTIVE_LOSSES"], expected)

    def test_schedule_cannot_silently_default_missing_history_to_zero(self):
        workflow = (ROOT / ".github" / "workflows" / "scan.yml").read_text(encoding="utf-8")
        self.assertIn("CONSECUTIVE_LOSSES: ${{ vars.CONSECUTIVE_LOSSES || '' }}", workflow)
        self.assertNotIn("CONSECUTIVE_LOSSES: ${{ vars.CONSECUTIVE_LOSSES || '0' }}", workflow)


    def test_all_missing_live_account_inputs_are_unknown(self):
        names = ("DAILY_PNL", "OPEN_RISK", "CONCURRENT_POSITIONS",
                 "CORRELATED_OPEN_RISK", "ACCOUNT_DRAWDOWN_PCT")
        with patch.dict(os.environ, {name: "" for name in names}):
            cfg = runpy.run_path(str(ROOT / "src" / "config.py"))
        for name in names:
            with self.subTest(name=name):
                self.assertIsNone(cfg[name])

    def test_explicit_zero_is_not_erased(self):
        names = ("DAILY_PNL", "OPEN_RISK", "CONCURRENT_POSITIONS",
                 "CORRELATED_OPEN_RISK", "ACCOUNT_DRAWDOWN_PCT")
        with patch.dict(os.environ, {name: "0" for name in names}):
            cfg = runpy.run_path(str(ROOT / "src" / "config.py"))
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(cfg[name], 0)

    def test_schedule_does_not_invent_empty_book_or_pnl(self):
        workflow = (ROOT / ".github" / "workflows" / "scan.yml").read_text(encoding="utf-8")
        names = ("DAILY_PNL", "OPEN_RISK", "CONCURRENT_POSITIONS",
                 "CORRELATED_OPEN_RISK", "ACCOUNT_DRAWDOWN_PCT")
        for name in names:
            with self.subTest(name=name):
                self.assertIn(name + ": ${{ vars." + name + " || '' }}", workflow)
                self.assertNotIn(name + ": ${{ vars." + name + " || '0' }}", workflow)


    def test_canonical_scan_enforces_execution_cost_gate(self):
        # In src/config.py the generic research default is disabled.  The
        # canonical scan must explicitly opt in to the stricter live gate.
        workflow = (ROOT / ".github" / "workflows" / "scan.yml").read_text(encoding="utf-8")
        scanner_step = workflow.split("      - name: Run scanner", 1)[1].split(
            "      - name: Publish all MCR research observations", 1
        )[0]
        self.assertIn('EXEC_ENFORCE_GATE: "1"', scanner_step)
        self.assertEqual(scanner_step.count("EXEC_ENFORCE_GATE:"), 1)

    def test_cost_gate_blocks_unverified_inputs_and_low_after_cost_rr(self):
        from src.execution_engine import ExecutionCostPolicy, evaluate_execution_rr, execution_gate

        incomplete = evaluate_execution_rr(
            entry=50, stop=48.5, target=53,
            policy=ExecutionCostPolicy(enforce_gate=True),
        )
        self.assertEqual(execution_gate(incomplete), (False, "EXECUTION_INPUT_REQUIRED"))
        self.assertIsNone(incomplete["execution_adjusted_rr"])

        expensive = evaluate_execution_rr(
            entry=50, stop=48.5, target=53,
            policy=ExecutionCostPolicy(
                buy_commission_rate=0.001, sell_commission_rate=0.001,
                sell_tax_rate=0.003, entry_slippage_bps=10,
                exit_slippage_bps=10, spread_bps=20,
                liquidity_penalty_bps=5, min_execution_rr=1.95,
                enforce_gate=True,
            ),
        )
        self.assertEqual(expensive["status"], "COMPLETE")
        self.assertEqual(execution_gate(expensive), (False, "EXECUTION_RR_BELOW_MINIMUM"))


if __name__ == "__main__":
    unittest.main()
