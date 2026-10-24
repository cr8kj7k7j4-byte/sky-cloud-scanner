import tempfile
from pathlib import Path

from src.model_registry import ModelRecord, register_model, registry_snapshot
from src.trade_logger import TradeRecord, evaluate_trade_record, append_trade
from src.readiness import default_sky100_checks, engineering_readiness


def main():
    with tempfile.TemporaryDirectory() as td:
        registry = Path(td) / "registry.json"
        weak = ModelRecord(
            name="rule_baseline",
            version="1.0",
            status="research",
            production_eligible=False,
            metrics={"expectancy_r": 0.05, "profit_factor": 1.05},
            validation={"oos": False},
        )
        strong = ModelRecord(
            name="xgb_candidate",
            version="1.1",
            status="validated",
            production_eligible=True,
            metrics={
                "expectancy_r": 0.12,
                "profit_factor": 1.25,
                "max_drawdown_r": 4.0,
                "stability_score": 0.8,
            },
            validation={"walk_forward": True, "oos": True},
        )
        register_model(registry, weak)
        register_model(registry, strong)
        snap = registry_snapshot(registry)
        assert snap["champion"]["name"] == "xgb_candidate"

        trade = TradeRecord(
            symbol="2409",
            side="LONG",
            entry_time="2026-10-21T09:30:00+08:00",
            entry_price=37.0,
            exit_time="2026-10-21T10:30:00+08:00",
            exit_price=37.8,
            quantity=1000,
            initial_stop=36.6,
            fees=50,
            tax=100,
            slippage=30,
            max_price_during_trade=38.0,
            min_price_during_trade=36.9,
            setup="P3",
            model_version="Sky-v1.4",
        )
        result = evaluate_trade_record(trade)
        assert result["gross_pnl"] == 800.0
        assert result["net_pnl"] == 620.0
        assert result["mfe_amount"] == 1000.0
        assert result["mae_amount"] == 100.0
        assert result["r_multiple"] == 1.55
        assert append_trade(Path(td) / "trades.jsonl", trade)["symbol"] == "2409"

        checks = default_sky100_checks(
            official_data_chain=True,
            feature_contract=True,
            decision_engine=True,
            risk_engine=True,
            trade_logging=True,
            walk_forward=True,
            oos=True,
            cost_stress=True,
            leakage_check=True,
            paper_trade=False,
            monitoring=False,
        )
        readiness = engineering_readiness(checks)
        assert readiness["score"] < 100
        assert readiness["production_ready"] is False
        assert "Paper Trading" in readiness["blocking_components"]

    print("PASS Sky 100 core tests")


if __name__ == "__main__":
    main()
