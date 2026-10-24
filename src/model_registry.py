from dataclasses import dataclass, asdict
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
MODEL_REGISTRY_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ModelCard:
    name: str
    version: str
    model_type: str
    target: str
    trained_until: str | None
    validation_status: str
    production_eligible: bool
    metrics: dict
    notes: str

    def to_dict(self):
        return asdict(self)


def baseline_model_card():
    return ModelCard(
        name="sky-ranking-transparent-baseline",
        version="0.1",
        model_type="RULE_BASED_BASELINE",
        target="expected_r",
        trained_until=None,
        validation_status="RESEARCH_ONLY",
        production_eligible=False,
        metrics={},
        notes="未訓練模型；只用於驗證 ranking contract 與後續模型比較流程。",
    )


def can_promote(model_card, *, min_trades=200, min_oos_pf=1.10, min_oos_expectancy_r=0.05, max_drawdown_r=None):
    card = model_card.to_dict() if hasattr(model_card, "to_dict") else dict(model_card or {})
    metrics = dict(card.get("metrics") or {})
    reasons = []
    if int(metrics.get("oos_trades") or 0) < min_trades:
        reasons.append("OOS樣本數不足")
    if float(metrics.get("oos_pf") or 0.0) < min_oos_pf:
        reasons.append("OOS PF 未達門檻")
    if float(metrics.get("oos_expectancy_r") or 0.0) < min_oos_expectancy_r:
        reasons.append("OOS Expectancy 未達門檻")
    if max_drawdown_r is not None and metrics.get("oos_max_drawdown_r") is not None:
        if abs(float(metrics["oos_max_drawdown_r"])) > abs(float(max_drawdown_r)):
            reasons.append("OOS 最大回撤超過門檻")
    return {
        "allowed": not reasons,
        "reasons": reasons,
        "checked_at": datetime.now(TZ).isoformat(),
        "schema_version": MODEL_REGISTRY_SCHEMA_VERSION,
    }
