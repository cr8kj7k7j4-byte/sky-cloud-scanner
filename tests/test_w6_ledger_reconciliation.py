"""W6 deterministic reconciliation checks. Fixtures are NEVER broker evidence."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta

from src.w6_ledger_reconciliation import reconcile_for_review

NOW = datetime(2026, 11, 9, 2, 0, tzinfo=timezone.utc)
DATE = "2026-11-09"
def fixture():
    return {
        "captured_at": "2026-11-09T09:59:30+08:00",
        "trading_date": DATE,
        "source": "SYNTHETIC_REVIEW_FIXTURE_NOT_BROKER",
        "account_equity": 500000,
        "positions_complete": True,
        "closed_trades_complete": True,
        "positions": [{"symbol": "1111", "side": "LONG", "quantity": 1000, "entry_price": 50, "stop_price": 48}],
        "closed_trades": [
            {"trade_id": "t1", "fill_id": "f1", "symbol": "2222", "side": "LONG",
             "entry_time": "2026-11-09T09:02:00+08:00", "exit_time": "2026-11-09T09:10:00+08:00",
             "quantity": 1000, "entry_price": 20, "exit_price": 19, "fees": 6, "tax": 28,
             "slippage": 3, "exit_reason": "STOP_LOSS"},
            {"trade_id": "t2", "fill_id": "f2", "symbol": "3333", "side": "LONG",
             "entry_time": "2026-11-09T09:20:00+08:00", "exit_time": "2026-11-09T09:32:00+08:00",
             "quantity": 1000, "entry_price": 30, "exit_price": 28, "fees": 9, "tax": 42,
             "slippage": 3, "exit_reason": "STOP_LOSS"},
        ],
    }

def test_derived_stops_and_pnl_are_hold_only():
    r = reconcile_for_review(fixture(), now=NOW)
    assert r["status"] == "HOLD_UNVERIFIED_SOURCE"
    assert r["portfolio_allowed"] is False
    assert r["ledger_verified"] is False
    assert r["derived"]["consecutive_stop_losses"] == 2
    assert r["derived"]["daily_pnl"] == -3091.0
    assert r["derived"]["open_risk"] == 2000.0
    assert r["derived"]["concurrent_positions"] == 1
    assert r["derived"]["correlated_open_risk"] is None
    assert r["derived"]["drawdown_pct"] is None
    assert len(r["input_sha256"]) == 64

def test_streak_resets_after_any_other_close():
    data = fixture()
    data["closed_trades"][1]["exit_reason"] = "OTHER"
    assert reconcile_for_review(data, now=NOW)["derived"]["consecutive_stop_losses"] == 0

def test_conflicting_or_duplicate_fills_rejected():
    data = fixture()
    data["closed_trades"][1]["fill_id"] = "f1"
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"

def test_ambiguous_close_order_rejected():
    data = fixture()
    data["closed_trades"][1]["exit_time"] = data["closed_trades"][0]["exit_time"]
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"

def test_missing_stop_or_position_scope_rejected():
    data = fixture()
    del data["positions"][0]["stop_price"]
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"
    data = fixture()
    data["positions_complete"] = False
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"

def test_stale_future_naive_and_wrong_session_rejected():
    data = fixture()
    assert reconcile_for_review(data, now=NOW + timedelta(minutes=10))["status"] == "BLOCK"
    data["captured_at"] = "2026-11-09T10:04:00+08:00"
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"
    data["captured_at"] = "2026-11-09T10:00:00"
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"
    data = fixture()
    data["closed_trades"][1]["exit_time"] = "2026-11-08T09:32:00+08:00"
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"

def test_claimed_real_source_never_authorizes():
    data = fixture()
    data["source"] = "BROKER_VERIFIED"  # Caller text is untrusted.
    data["ledger_verified"] = True
    data["ledger_fresh"] = True
    r = reconcile_for_review(data, now=NOW)
    assert r["status"] == "HOLD_UNVERIFIED_SOURCE"
    assert r["portfolio_allowed"] is False
    assert r["ledger_verified"] is False

def test_nan_and_bogus_fees_are_rejected():
    data = fixture()
    data["closed_trades"][0]["fees"] = float("nan")
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"
    data = fixture()
    data["account_equity"] = "Infinity"
    assert reconcile_for_review(data, now=NOW)["status"] == "BLOCK"


if __name__ == "__main__":
    test_derived_stops_and_pnl_are_hold_only()
    test_streak_resets_after_any_other_close()
    test_conflicting_or_duplicate_fills_rejected()
    test_ambiguous_close_order_rejected()
    test_missing_stop_or_position_scope_rejected()
    test_stale_future_naive_and_wrong_session_rejected()
    test_claimed_real_source_never_authorizes()
    test_nan_and_bogus_fees_are_rejected()
    print("PASS W6 ledger reconciliation review-only checks")
