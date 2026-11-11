"""Static research wiring contract; not a substitute for paid runtime proof."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AtomicWorkflowWiringTests(unittest.TestCase):
    def test_entitlement_probe_is_manual_only_with_atomic_paid_step(self):
        w = (ROOT / ".github/workflows/fugle-2026-entitlement-probe.yml").read_text()
        source = (ROOT / "research/fugle_2026_entitlement_probe.py").read_text()
        step = w.split("      - name: Live two-symbol historical API capability check", 1)[1]
        step = step.split("      - name:", 1)[0]
        self.assertIn("if: github.event_name != 'pull_request'", step)
        self.assertIn("SKY_PAID_ATOMIC_ENFORCE: '1'", step)
        self.assertIn("GH_TOKEN: ${{ github.token }}", step)
        self.assertIn("contents: write", w)
        self.assertIn("guard_fugle_request(", source)
        self.assertLess(source.index("guard_fugle_request(f"), source.index("response = get("))
        self.assertIn("sky_paid_reservation:", w)

    def test_stage2_paid_step_has_atomic_gate(self):
        workflow = (ROOT / ".github/workflows/sky-fugle-stage2-probe.yml").read_text()
        source = (ROOT / "src/sky_fugle_stage2_probe.py").read_text()
        paid = workflow.split("      - name: Probe 2 market snapshots and 2 individual quotes", 1)[1]
        paid = paid.split("      - name:", 1)[0]
        self.assertIn("SKY_PAID_ATOMIC_ENFORCE: '1'", paid)
        self.assertIn("GH_TOKEN: ${{ github.token }}", paid)
        self.assertIn("verify_claim.outcome == 'success'", paid)
        self.assertIn("contents: write", workflow)
        self.assertIn("guard_fugle_request(BASE + path, params)", source)
        self.assertLess(source.index("guard_fugle_request(BASE + path, params)"),
                        source.index("response = request(BASE + path"))

    def test_bridge_paid_step_has_research_atomic_gate(self):
        w = (ROOT / ".github/workflows/sky-chat-bridge.yml").read_text()
        source = (ROOT / "src/fugle.py").read_text()
        paid = w.split("      - name: Run read-only paid Fugle observations", 1)[1]
        paid = paid.split("      - name:", 1)[0]
        self.assertIn("SKY_PAID_ATOMIC_ENFORCE: '1'", paid)
        self.assertIn("GH_TOKEN: ${{ github.token }}", paid)
        self.assertIn("verify_claim.outcome == 'success'", paid)
        self.assertIn("guard_fugle_request(BASE + path, params)", source)


if __name__ == "__main__":
    unittest.main()
