from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ValidationGate:
    walk_forward_passed: bool
    oos_passed: bool
    cost_stress_passed: bool
    leakage_check_passed: bool
    paper_trade_passed: bool

    def to_dict(self):
        return asdict(self)

    @property
    def production_eligible(self):
        return all([
            self.walk_forward_passed,
            self.oos_passed,
            self.cost_stress_passed,
            self.leakage_check_passed,
            self.paper_trade_passed,
        ])


def evaluate_validation_gate(
    *,
    walk_forward_passed=False,
    oos_passed=False,
    cost_stress_passed=False,
    leakage_check_passed=False,
    paper_trade_passed=False,
):
    gate = ValidationGate(
        walk_forward_passed=bool(walk_forward_passed),
        oos_passed=bool(oos_passed),
        cost_stress_passed=bool(cost_stress_passed),
        leakage_check_passed=bool(leakage_check_passed),
        paper_trade_passed=bool(paper_trade_passed),
    )
    return {
        **gate.to_dict(),
        "production_eligible": gate.production_eligible,
        "status": "PRODUCTION_ELIGIBLE" if gate.production_eligible else "RESEARCH_ONLY",
    }
