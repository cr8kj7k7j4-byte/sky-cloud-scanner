import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.risk_engine import RiskPolicy, drawdown_state, evaluate_trade, position_size, evaluate_candidate


def main():
    p = RiskPolicy(lot_size=1000)

    assert drawdown_state(0, 0, p) == "NORMAL"
    assert drawdown_state(0, 3, p) == "CAUTION"
    assert drawdown_state(0, 5, p) == "DEFENSIVE"
    assert drawdown_state(0.06, 0, p) == "LOCKDOWN"

    missing = evaluate_trade(
        entry=50,
        stop=None,
        target=None,
        account_equity=500000,
        policy=p,
    )
    assert missing["status"] == "RISK_INPUT_REQUIRED"
    assert missing["portfolio_allowed"] is False

    ok = evaluate_trade(
        entry=50,
        stop=48.5,
        target=53,
        account_equity=500000,
        daily_pnl=0,
        open_risk=0,
        concurrent_positions=0,
        correlated_open_risk=0,
        drawdown_pct=0,
        consecutive_losses=0,
        grade="A+",
        policy=p,
    )
    assert ok["status"] == "ALLOW"
    assert ok["recommended_shares"] == 1000
    assert ok["net_rr"] == 2.0

    loss_lock = evaluate_trade(
        entry=50,
        stop=48.5,
        target=53,
        account_equity=500000,
        daily_pnl=-7500,
        grade="A+",
        policy=p,
    )
    assert loss_lock["status"] == "BLOCK"

    dd_lock = evaluate_trade(
        entry=50,
        stop=48.5,
        target=53,
        account_equity=500000,
        drawdown_pct=0.06,
        grade="A+",
        policy=p,
    )
    assert dd_lock["state"] == "LOCKDOWN"
    assert dd_lock["status"] == "BLOCK"

    # Same existing P0-R CI job executes this manual-holdings smoke contract.
    from datetime import datetime, timezone, timedelta
    from src.sky_manual_position_review import parse_manual_positions, review_manual_positions
    tpe = timezone(timedelta(hours=8))
    now = datetime(2026, 11, 27, 10, 30, tzinfo=tpe)
    parsed = parse_manual_positions("Sky 持股檢查 2330 1張 成本850 停損820")
    assert parsed["status"] == "PASS_INPUT"
    assert parsed["positions"][0]["shares"] == 1000
    missing_account = review_manual_positions("Sky 持股檢查 2330 1張 成本850 停損820", now=now)
    assert missing_account["status"] == "HOLD"
    assert missing_account["new_entry_allowed"] is False
    assert "HOLD_MISSING_ACCOUNT_CONTEXT" in missing_account["reasons"]
    print("PASS SKY MANUAL POSITION INPUT FAIL-CLOSED SMOKE")

    print("PASS P0-R risk engine tests")


if __name__ == "__main__":
    main()


def test_long_stop_above_entry_is_never_tradable():
    """For the long-only P0-R entry gate, reversed stops must fail closed."""
    policy = RiskPolicy(lot_size=1000)
    for stop in (50, 50.5, 52):
        result = evaluate_trade(
            entry=50, stop=stop, target=55, account_equity=500000,
            daily_pnl=0, open_risk=0, concurrent_positions=0,
            correlated_open_risk=0, drawdown_pct=0,
            consecutive_losses=0, grade="A+", policy=policy,
        )
        assert result["status"] == "BLOCK"
        assert result["portfolio_allowed"] is False
        assert result["recommended_shares"] == 0
        assert any("停損價必須低於進場價" in reason for reason in result["reasons"])
        assert position_size(50, stop, 500000, policy=policy) == 0
    # A valid below-entry protective stop retains ordinary sizing behaviour.
    assert position_size(50, 48.5, 500000, policy=policy) > 0


def test_account_context_nonfinite_and_negative_exposure_never_approves_entry():
    """P0-R: malformed account context cannot be treated as a flat book."""
    candidate = {"entry": 50, "stop": 48.5, "target": 55, "grade": "A+"}
    verified = {
        "account_equity": 500000, "daily_pnl": 0.0, "open_risk": 0.0,
        "concurrent_positions": 0, "correlated_open_risk": 0.0,
        "drawdown_pct": 0.0, "consecutive_losses": 0,
    }
    assert evaluate_candidate(candidate, verified)["status"] == "ALLOW"
    for key, value in (
        ("daily_pnl", float("nan")),
        ("open_risk", float("nan")),
        ("open_risk", -1.0),
        ("correlated_open_risk", -1.0),
        ("drawdown_pct", -0.01),
        ("concurrent_positions", -1),
        ("consecutive_losses", -1),
        ("consecutive_losses", 0.5),
        ("account_equity", float("inf")),
        ("account_equity", True),
    ):
        result = evaluate_candidate(candidate, {**verified, key: value})
        assert result["status"] == "RISK_INPUT_INVALID", (key, value, result)
        assert result["portfolio_allowed"] is False
        assert result["recommended_shares"] == 0
        assert key in result["required_inputs"]
    # A verified loss is negative daily P&L; never reject valid reported losses.
    valid_loss = evaluate_candidate(candidate, {**verified, "daily_pnl": -3000.0})
    assert valid_loss["status"] == "ALLOW"


def test_nonfinite_or_malformed_trade_price_fails_closed():
    """Direct evaluation never approves or crashes for invalid prices/equity."""
    inputs = {
        "entry": 50, "stop": 48.5, "target": 55,
        "account_equity": 500000, "daily_pnl": 0,
        "open_risk": 0, "concurrent_positions": 0,
        "correlated_open_risk": 0, "drawdown_pct": 0,
        "consecutive_losses": 0, "grade": "A+",
    }
    for name, bad in (
        ("entry", float("nan")),
        ("stop", float("inf")),
        ("target", float("-inf")),
        ("entry", "not-a-price"),
        ("account_equity", float("inf")),
        ("target", True),
    ):
        result = evaluate_trade(**{**inputs, name: bad})
        assert result["status"] == "RISK_INPUT_INVALID", (name, bad, result)
        assert result["portfolio_allowed"] is False
        assert result["recommended_shares"] == 0
        assert name in result["required_inputs"]
    # Direct sizing must fail closed without raising floor(nan)/floor(inf).
    for args in (
        (float("nan"), 48.5, 500000),
        (50, float("inf"), 500000),
        (50, 48.5, float("inf")),
        ("bad-price", 48.5, 500000),
        (True, 48.5, 500000),
    ):
        assert position_size(*args) == 0
    # Positive control: ordinary finite prices and proper stop remain valid.
    assert position_size(50, 48.5, 500000, policy=RiskPolicy(lot_size=1000)) == 1000
