import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.shadow_trading import ShadowSignal, evaluate_shadow_trade
from src.shadow_promotion_gate import shadow_promotion_gate


def main():
    signal=ShadowSignal(
        signal_id="sig-1",
        symbol="2409",
        side="LONG",
        strategy_version="sky-v2.1",
        model_version="rule-engine-1.0",
        feature_schema_version="1.0.0",
        rule_config_version="2.1.0",
        generated_at="2026-10-25T09:30:00+08:00",
        entry_price=37.0,
        stop_price=36.5,
        target_price=38.0,
        quantity=1000,
        regime="BULL_MEDIUM",
        setup="P3",
        phase="P3",
    )
    result=evaluate_shadow_trade(
        signal,
        exit_time="2026-10-25T10:30:00+08:00",
        exit_price=37.8,
        max_price=38.1,
        min_price=36.9,
        fees=50,
        tax=100,
        slippage=30,
        exit_reason="TARGET_TRAIL",
    )
    assert result["mode"]=="SHADOW_ONLY"
    assert result["live_order_allowed"] is False
    assert result["net_pnl"]==620.0
    assert result["r_multiple"]==1.24
    assert result["mfe_r"]==2.2
    assert result["mae_r"]==0.2

    gate=shadow_promotion_gate(
        {
            "trades":120,
            "expectancy_r":0.12,
            "profit_factor":1.25,
            "max_drawdown_r":5.0,
            "mae_r_p95":1.1,
            "regime_count":3,
        },
        monitoring_clean=True,
        data_quality_clean=True,
    )
    assert gate["shadow_passed"] is True
    assert gate["production_eligible"] is False

    blocked=shadow_promotion_gate(
        {
            "trades":20,
            "expectancy_r":0.20,
            "profit_factor":1.5,
            "max_drawdown_r":3.0,
            "mae_r_p95":1.0,
            "regime_count":1,
        },
        monitoring_clean=True,
        data_quality_clean=True,
    )
    assert blocked["shadow_passed"] is False
    assert "sample_size" in blocked["failed_checks"]

    print("PASS Paper Trading + Shadow Deployment tests")


if __name__=="__main__":
    main()
