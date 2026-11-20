import unittest
from unittest.mock import patch
from research.sky_p0r_policy_runtime_drift import audit

class RuntimeDriftTest(unittest.TestCase):
    def test_real_main_configuration_is_not_misreported_as_safe(self):
        r = audit()
        by = {x["name"]:x for x in r["checks"]}
        self.assertTrue(by["capital_500k"]["passed"])
        self.assertTrue(by["daily_stop_at_10k"]["passed"])
        self.assertEqual(by["two_consecutive_losses_stop"]["passed"],
                         by["two_consecutive_losses_stop"]["observed"] == "BLOCK")
        self.assertEqual(by["missing_execution_inputs_block"]["passed"],
                         by["missing_execution_inputs_block"]["observed"]["risk"] == "BLOCK"
                         and by["missing_execution_inputs_block"]["observed"]["execution"] == "EXECUTION_INPUT_REQUIRED")
        self.assertFalse(r["risk_production_eligible"])
        self.assertFalse(r["paper_ledger_verified"])
        self.assertFalse(r["broker_account_required_for_research"])

    def test_two_loss_safety_requires_real_engine_block_not_config_label(self):
        from src import config
        with patch.object(config, "CAUTION_LOSS_STREAK", 2):
            # Merely changing a caution state does NOT turn it into a hard block.
            r = audit()
        check = next(c for c in r["checks"] if c["name"]=="two_consecutive_losses_stop")
        self.assertEqual(check["passed"], check["observed"] == "BLOCK")

    def test_enforced_execution_gate_missing_inputs_blocks_synthetic_trade(self):
        from src import config
        with patch.object(config, "EXEC_ENFORCE_GATE", True):
            r=audit()
        self.assertTrue(next(c for c in r["checks"] if c["name"]=="missing_execution_inputs_block")["passed"])
        self.assertFalse(r["risk_production_eligible"])

    def test_never_uses_fake_ledger_or_infers_trade_ready(self):
        r=audit()
        self.assertFalse(r["current_portfolio_ledger_verified"])
        self.assertFalse(r["real_slippage_and_fill_verified"])
        self.assertFalse(r["automatic_order"])
        self.assertEqual(r["trade_action"],"禁止交易")
        self.assertIn(r["verdict"],("CONFIG_AND_EVIDENCE_BLOCKED","PAPER_LEDGER_AND_EXECUTION_EVIDENCE_REQUIRED"))

if __name__=="__main__":
    unittest.main()
