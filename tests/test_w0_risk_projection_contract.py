"""W0 integration regression: missing account ledger must render as HOLD, not crash.

Based on W6 #365 draft; no live broker/Cloud Run claims.
"""
from src.main import _annotate_risk_display
from src.risk_engine import evaluate_candidate


def test_missing_authoritative_ledger_risk_response_is_renderable():
    candidate = {"entry": 50, "stop": 48, "target": 56, "grade": "A+"}
    # These zeroes intentionally demonstrate that numerical defaults are not proof.
    context = {"account_equity": 500000, "daily_pnl": 0,
               "open_risk": 0, "concurrent_positions": 0,
               "consecutive_losses": 0}
    result = _annotate_risk_display(evaluate_candidate(candidate, context))
    assert result["status"] == "RISK_INPUT_REQUIRED"
    assert result["portfolio_allowed"] is False
    assert result["recommended_shares"] == 0
    assert result["state_zh"] == "未知／資料不足"
    assert "ledger_verified" in result["required_inputs"]


def test_ordinary_risk_state_remains_localized():
    risk = {"status": "BLOCK", "state": "LOCKDOWN", "portfolio_allowed": False}
    result = _annotate_risk_display(risk)
    assert result["state_zh"] == "鎖定"
    assert result["status_zh"]
