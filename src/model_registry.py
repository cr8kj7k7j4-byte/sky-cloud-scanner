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
