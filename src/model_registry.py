from dataclasses import dataclass, asdict
from pathlib import Path
import json


@dataclass(frozen=True)
class ModelRecord:
    name: str
    version: str
    status: str
    production_eligible: bool
    metrics: dict
    validation: dict
    notes: str = ""

    def to_dict(self):
        return asdict(self)


def _load(path):
    p = Path(path)
    if not p.exists():
        return {"champion": None, "challengers": [], "history": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(path, payload):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def register_model(path, record):
    payload = _load(path)
    item = record.to_dict() if isinstance(record, ModelRecord) else dict(record)
    payload.setdefault("history", []).append(item)

    if item.get("production_eligible"):
        current = payload.get("champion")
        if current is None:
            payload["champion"] = item
        else:
            new_score = _selection_score(item.get("metrics", {}))
            old_score = _selection_score(current.get("metrics", {}))
            if new_score > old_score:
                payload.setdefault("challengers", []).append(current)
                payload["champion"] = item
            else:
                payload.setdefault("challengers", []).append(item)
    else:
        payload.setdefault("challengers", []).append(item)

    _save(path, payload)
    return payload


def _selection_score(metrics):
    """
    Engineering ranking only.
    It is NOT a probability of profit and NOT a guarantee of future returns.
    Preference: positive expectancy/PF, lower drawdown, and stability.
    """
    expectancy_r = float(metrics.get("expectancy_r") or 0.0)
    profit_factor = float(metrics.get("profit_factor") or 0.0)
    max_drawdown_r = abs(float(metrics.get("max_drawdown_r") or 0.0))
    stability = float(metrics.get("stability_score") or 0.0)
    return (
        expectancy_r * 4.0
        + max(profit_factor - 1.0, 0.0) * 2.0
        + stability
        - max_drawdown_r * 0.5
    )


def registry_snapshot(path):
    return _load(path)


# Legacy research compatibility API. Canonical governance remains P0-G.
def baseline_model_card():
    return ModelRecord(
        name="sky-ranking-transparent-baseline",
        version="0.1",
        status="RESEARCH_ONLY",
        production_eligible=False,
        metrics={},
        validation={"status": "RESEARCH_ONLY"},
        notes="未訓練模型；僅用於 ranking contract 與歷史研究重現。",
    )


def can_promote(model_card, *, min_trades=200, min_oos_pf=1.10,
                min_oos_expectancy_r=0.05, max_drawdown_r=None):
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
    return {"allowed": not reasons, "reasons": reasons, "schema_version": "compat-1.0"}
