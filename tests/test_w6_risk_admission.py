"""W6 candidate admission checks; no broker or live account access is simulated."""
from src.risk_engine import RiskPolicy, evaluate_candidate, evaluate_trade
from src.execution_engine import ExecutionCostPolicy

P = RiskPolicy(risk_per_trade_pct=.01, daily_loss_limit_pct=.02, max_portfolio_heat_pct=.03, max_position_pct=.20, max_concurrent_positions=3)
C = {"entry": 50, "stop": 48, "target": 56, "grade": "A+"}
COST = ExecutionCostPolicy(buy_commission_rate=.000333, sell_commission_rate=.000333, sell_tax_rate=.0015, entry_slippage_bps=5, exit_slippage_bps=5, spread_bps=5, liquidity_penalty_bps=5, enforce_gate=True)
CTX = dict(account_equity=500000, daily_pnl=0, open_risk=0, concurrent_positions=0, correlated_open_risk=0, drawdown_pct=0, consecutive_losses=0, ledger_verified=True, ledger_fresh=True, ledger_complete=True, ledger_source="test_fixture_only", ledger_asof="2026-11-08T10:00:00+08:00", execution_policy=COST)

def test_unknown_state_blocks():
    for field in ("daily_pnl", "consecutive_losses", "open_risk", "concurrent_positions", "account_equity"):
        ctx = dict(CTX)
        del ctx[field]
        result = evaluate_candidate(C, ctx, P)
        assert result["portfolio_allowed"] is False
        assert field in result["required_inputs"]
        assert result["recommended_shares"] == 0

def test_missing_ledger_proof_blocks():
    for field in ("ledger_verified", "ledger_asof", "ledger_source", "ledger_fresh", "ledger_complete"):
        ctx = dict(CTX)
        del ctx[field]
        assert evaluate_candidate(C, ctx, P)["portfolio_allowed"] is False

def test_cost_gate_unavailable_blocks():
    ctx = dict(CTX, execution_policy=ExecutionCostPolicy(enforce_gate=False))
    assert evaluate_candidate(C, ctx, P)["portfolio_allowed"] is False
    ctx["execution_policy"] = ExecutionCostPolicy(enforce_gate=True)
    assert evaluate_candidate(C, ctx, P)["execution_status"] == "EXECUTION_INPUT_REQUIRED"
    assert evaluate_candidate(C, ctx, P)["portfolio_allowed"] is False

def test_two_stops_block_and_one_stop_does_not():
    ctx = dict(CTX, consecutive_losses=2)
    result = evaluate_candidate(C, ctx, P)
    assert result["status"] == "BLOCK"
    assert result["recommended_shares"] == 0
    assert evaluate_candidate(C, dict(CTX, consecutive_losses=1), P)["status"] == "ALLOW"

def test_limits_and_stop_direction():
    assert evaluate_candidate(C, dict(CTX, daily_pnl=-10000), P)["status"] == "BLOCK"
    assert evaluate_candidate(C, dict(CTX, open_risk=15000), P)["status"] == "BLOCK"
    assert evaluate_candidate(C, dict(CTX, concurrent_positions=3), P)["status"] == "BLOCK"
    assert evaluate_candidate(dict(C, stop=51), CTX, P)["status"] == "BLOCK"
    allowed = evaluate_candidate(C, CTX, P)
    assert allowed["status"] == "ALLOW"
    assert allowed["recommended_shares"] * C["entry"] <= 100000
    assert allowed["proposed_risk"] <= 5000
    assert allowed["execution_adjusted_rr"] >= 1.5

def test_default_cost_gate_matches_p0r_355():
    import os
    import subprocess
    import sys
    env = dict(os.environ)
    env.pop("EXEC_ENFORCE_GATE", None)
    command = "from src.config import EXEC_ENFORCE_GATE; print(int(EXEC_ENFORCE_GATE))"
    result = subprocess.run([sys.executable, "-c", command],
                            check=True, capture_output=True, text=True, env=env)
    assert result.stdout.strip() == "1"


def test_p0r_355_hard_boundaries():
    args = dict(entry=50, stop=48, target=55, account_equity=500000,
                grade="A+", policy=P)
    ok = evaluate_trade(**args)
    assert ok["status"] == "ALLOW"
    assert ok["risk_budget"] == 5000
    assert ok["recommended_shares"] == 2000
    assert ok["proposed_risk"] == 4000
    assert ok["remaining_portfolio_heat"] == 15000
    for extra in ({"daily_pnl": -10000}, {"open_risk": 15000},
                  {"concurrent_positions": 3}, {"consecutive_losses": 2}):
        blocked = evaluate_trade(**args, **extra)
        assert blocked["status"] == "BLOCK"
        assert blocked["recommended_shares"] == 0
    assert evaluate_trade(**dict(args, stop=50))["status"] == "BLOCK"
    assert evaluate_trade(**dict(args, stop=51))["status"] == "BLOCK"


def test_malformed_account_state_is_never_safely_zero():
    for key, bad in (
        ("daily_pnl", float("nan")),
        ("open_risk", float("inf")),
        ("open_risk", -1),
        ("correlated_open_risk", -2),
        ("drawdown_pct", -0.01),
        ("concurrent_positions", 1.5),
        ("consecutive_losses", 0.5),
        ("consecutive_losses", "not available"),
        ("account_equity", True),
        ("account_equity", 0),
    ):
        ctx = dict(CTX, **{key: bad})
        decision = evaluate_candidate(C, ctx, P)
        assert decision["status"] == "RISK_INPUT_REQUIRED", (key, bad, decision)
        assert decision["recommended_shares"] == 0
        assert decision["portfolio_allowed"] is False
        assert key + "_invalid" in decision["required_inputs"]


def test_nonfinite_candidate_prices_fail_closed():
    for key, value in (
        ("entry", float("nan")), ("entry", True),
        ("stop", float("inf")), ("stop", "not reported"),
        ("target", float("-inf")), ("target", 0),
    ):
        candidate = dict(C, **{key: value})
        result = evaluate_candidate(candidate, CTX, P)
        assert result["status"] == "RISK_INPUT_REQUIRED", (key, value, result)
        assert result["portfolio_allowed"] is False
        assert result["recommended_shares"] == 0
        assert key + "_invalid" in result["required_inputs"]


def test_only_a_plus_can_enter_candidate_risk_admission():
    for grade in ("A", "X", None, "A++", "READY", 90):
        candidate = dict(C, grade=grade)
        result = evaluate_candidate(candidate, CTX, P)
        assert result["status"] == "BLOCK", (grade, result)
        assert result["portfolio_allowed"] is False
        assert result["recommended_shares"] == 0
        assert result["execution_status"] == "GRADE_NOT_ELIGIBLE"
    assert evaluate_candidate(C, CTX, P)["status"] == "ALLOW"


def test_ledger_timestamp_provenance_requires_valid_timezone():
    for bad in (
        "not-a-date", "2026-11-08T10:00:00",
        "2026-02-30T10:00:00+08:00",
        "2026-11-08", 123456, True, [],
    ):
        result = evaluate_candidate(C, dict(CTX, ledger_asof=bad), P)
        assert result["status"] == "RISK_INPUT_REQUIRED", (bad, result)
        assert result["portfolio_allowed"] is False
        assert result["recommended_shares"] == 0
        expected = "ledger_asof_invalid" if bad else "ledger_asof"
        assert expected in result["required_inputs"], (bad, result)

    for bad in (False, 123, [], "   "):
        result = evaluate_candidate(C, dict(CTX, ledger_source=bad), P)
        assert result["status"] == "RISK_INPUT_REQUIRED", (bad, result)
        assert result["portfolio_allowed"] is False
        assert result["recommended_shares"] == 0
        expected = "ledger_source_invalid" if bad else "ledger_source"
        assert expected in result["required_inputs"], (bad, result)

    # Format validation is not authenticated provenance or true freshness.
    for asof in ("2026-11-08T10:00:00+08:00", "2026-11-08T02:00:00Z"):
        result = evaluate_candidate(C, dict(CTX, ledger_asof=asof), P)
        assert result["status"] == "ALLOW", (asof, result)


def test_integer_count_wire_format_cannot_crash_admission():
    # An upstream JSON string "1.0" used to pass float validation but raise
    # ValueError inside evaluate_trade's int("1.0"), aborting the scan.
    for key in ("concurrent_positions", "consecutive_losses"):
        for raw in ("1.0", "1e0", " 1 ", "-0", "not_available"):
            result = evaluate_candidate(C, dict(CTX, **{key: raw}), P)
            assert result["status"] == "RISK_INPUT_REQUIRED", (key, raw, result)
            assert result["portfolio_allowed"] is False
            assert result["recommended_shares"] == 0
            assert key + "_invalid" in result["required_inputs"]
        # A canonical integer string from an authenticated feed remains
        # parseable by the legacy arithmetic helper; this is not proof of origin.
        valid = evaluate_candidate(C, dict(CTX, **{key: "1"}), P)
        assert valid["status"] == "ALLOW", (key, valid)


def test_default_risk_policy_matches_confirmed_500k_p0r():
    defaults = RiskPolicy()
    assert defaults.risk_per_trade_pct == 0.01
    assert defaults.daily_loss_limit_pct == 0.02
    assert defaults.max_portfolio_heat_pct == 0.03
    assert defaults.max_position_pct == 0.20
    assert defaults.max_concurrent_positions == 3
    assert defaults.stop_after_consecutive_losses == 2
    decision = evaluate_trade(
        entry=50, stop=48, target=55, account_equity=500000,
        policy=defaults, grade="A+",
    )
    assert decision["risk_budget"] == 5000
    assert decision["remaining_daily_risk_budget"] == 10000
    assert decision["remaining_portfolio_heat"] == 15000
    assert decision["recommended_shares"] * 50 <= 100000
    for blocked in (
        {"daily_pnl": -10000},
        {"open_risk": 15000},
        {"concurrent_positions": 3},
        {"consecutive_losses": 2},
    ):
        assert evaluate_trade(
            entry=50, stop=48, target=55, account_equity=500000,
            policy=defaults, grade="A+", **blocked,
        )["status"] == "BLOCK"


if __name__ == "__main__":
    test_unknown_state_blocks()
    test_missing_ledger_proof_blocks()
    test_cost_gate_unavailable_blocks()
    test_two_stops_block_and_one_stop_does_not()
    test_limits_and_stop_direction()
    test_default_cost_gate_matches_p0r_355()
    test_p0r_355_hard_boundaries()
    test_malformed_account_state_is_never_safely_zero()
    test_nonfinite_candidate_prices_fail_closed()
    test_only_a_plus_can_enter_candidate_risk_admission()
    test_default_risk_policy_matches_confirmed_500k_p0r()
    test_integer_count_wire_format_cannot_crash_admission()
    test_ledger_timestamp_provenance_requires_valid_timezone()
    print("PASS W6 candidate fail-closed checks")
