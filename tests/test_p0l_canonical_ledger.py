import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.trade_logger import (
    TRADE_LEDGER_SCHEMA_VERSION,
    TradeRecord,
    build_trade_decision_record,
    evaluate_trade_record,
    append_trade,
    build_canonical_ledger_entry,
)
from src.trade_log import TRADE_LOG_SCHEMA_VERSION
from src.outcome_engine import evaluate_long_outcome


def main():
    assert TRADE_LOG_SCHEMA_VERSION == TRADE_LEDGER_SCHEMA_VERSION

    decision = build_trade_decision_record(
        item={
            "symbol": "2409",
            "name": "友達",
            "exchange": "TWSE",
            "last": 37.0,
            "entry": 37.0,
            "stop": 36.6,
            "target": 37.8,
            "risk": {"status": "ALLOW", "net_rr": 2.0},
            "features": {"momentum_1": 0.2},
        },
        run_id="run-1",
    )
    assert decision.schema_version == TRADE_LEDGER_SCHEMA_VERSION
    assert decision.symbol == "2409"

    trade = TradeRecord(
        symbol="2409",
        side="LONG",
        entry_time="2026-10-25T09:30:00+08:00",
        entry_price=37.0,
        exit_time="2026-10-25T10:30:00+08:00",
        exit_price=37.8,
        quantity=1000,
        initial_stop=36.6,
        fees=50,
        tax=100,
        slippage=30,
        max_price_during_trade=38.0,
        min_price_during_trade=36.9,
        setup="P3",
        phase="P3",
        model_version="rule-engine-1.0",
        decision_record_id=decision.record_id,
        strategy_version="sky-v2.1",
        feature_schema_version="1.0.0",
        rule_config_version="2.1.0",
    )
    result = evaluate_trade_record(trade)
    assert result["schema_version"] == TRADE_LEDGER_SCHEMA_VERSION
    assert result["decision_record_id"] == decision.record_id
    assert result["net_pnl"] == 620.0
    assert result["r_multiple"] == 1.55
    assert result["mfe_r"] == 2.5
    assert result["mae_r"] == 0.25

    outcome = evaluate_long_outcome(
        entry=37.0,
        stop=36.6,
        target=37.8,
        bars=[
            {"high": 37.4, "low": 36.9, "close": 37.2},
            {"high": 38.0, "low": 37.1, "close": 37.8},
        ],
        exit_price=37.8,
    )
    entry = build_canonical_ledger_entry(
        decision,
        {**result, "outcome": outcome.to_dict()},
    )
    assert entry["decision"]["record_id"] == decision.record_id
    assert entry["trade"]["r_multiple"] == 1.55
    assert entry["outcome"]["status"] == "COMPLETE"

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "trades.jsonl"
        written = append_trade(p, trade)
        assert written["symbol"] == "2409"
        assert p.exists()

    print("PASS P0-L canonical trade ledger tests")


if __name__ == "__main__":
    main()
