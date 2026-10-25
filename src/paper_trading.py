from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json


PASS_VERDICT = "PASS_TO_PAPER_TRADING"


@dataclass(frozen=True)
class PaperTradingGate:
    mode: str
    oos_verdict: str
    enabled: bool
    simulation_allowed: bool
    reason: str

    def to_dict(self):
        return asdict(self)


def evaluate_paper_gate(mode: str, oos_verdict: str) -> PaperTradingGate:
    mode = str(mode or "shadow").strip().lower()
    verdict = str(oos_verdict or "RESEARCH_ONLY").strip().upper()

    if mode not in {"off", "shadow", "paper"}:
        raise ValueError("PAPER_TRADING_MODE must be off, shadow, or paper")

    if mode == "off":
        return PaperTradingGate(
            mode=mode,
            oos_verdict=verdict,
            enabled=False,
            simulation_allowed=False,
            reason="Paper Trading 已停用",
        )

    if mode == "shadow":
        return PaperTradingGate(
            mode=mode,
            oos_verdict=verdict,
            enabled=True,
            simulation_allowed=False,
            reason="Shadow 模式：只記錄候選，不模擬成交",
        )

    if verdict != PASS_VERDICT:
        return PaperTradingGate(
            mode=mode,
            oos_verdict=verdict,
            enabled=True,
            simulation_allowed=False,
            reason="OOS Gate 尚未通過，禁止模擬成交",
        )

    return PaperTradingGate(
        mode=mode,
        oos_verdict=verdict,
        enabled=True,
        simulation_allowed=True,
        reason="OOS Gate 通過，可進 Paper Trading；仍禁止真實委託",
    )


def build_paper_snapshot(*, run_id: str, observed_at: str, item: dict, gate: PaperTradingGate):
    item = dict(item or {})
    risk = dict(item.get("risk") or {})
    monitor = dict(item.get("monitor") or {})
    decision = dict(item.get("decision") or {})
    plan = dict(item.get("strategy_plan") or {})

    trigger = plan.get("trigger")
    stop = plan.get("stop")
    risk_per_share = None
    try:
        if trigger is not None and stop is not None:
            risk_per_share = abs(float(trigger) - float(stop))
    except (TypeError, ValueError):
        risk_per_share = None

    return {
        "schema_version": "1.2",
        "run_id": str(run_id),
        "observed_at": str(observed_at),
        "observation_timestamp": str(observed_at),
        "strategy_id": item.get("strategy_id"),
        "strategy_version": item.get("strategy_version"),
        "symbol": str(item.get("symbol") or ""),
        "name": str(item.get("name") or ""),
        "exchange": item.get("exchange"),
        "market_regime": (
            ((item.get("ml") or {}).get("regime") or {}).get("label")
            if isinstance((item.get("ml") or {}).get("regime"), dict)
            else (item.get("ml") or {}).get("regime")
        ),
        "sector": item.get("sector"),
        "ranking_position": item.get("ranking_position"),
        "rank_score": item.get("rank_score"),
        "phase": plan.get("phase") or item.get("phase"),
        "setup": plan.get("setup"),
        "trigger": plan.get("trigger"),
        "trigger_price": plan.get("trigger"),
        "assumed_entry": plan.get("entry") or plan.get("trigger"),
        "max_acceptable_price": plan.get("max_entry"),
        "stop": plan.get("stop"),
        "target_1": plan.get("target"),
        "target_2": plan.get("target_2"),
        "p0_r_decision": risk.get("status"),
        "risk_per_share": risk_per_share,
        "data_quality": dict(item.get("data_quality") or {}),
        "missing_data": list(item.get("missing_data") or []),
        "outcome_completeness": item.get("outcome_completeness"),
        "market": {
            "last": item.get("last"),
            "change_pct": item.get("change_pct"),
            "volume": item.get("volume"),
            "trade_value": item.get("trade_value"),
            "quote_time": item.get("quote_time"),
            "quote_source": item.get("quote_source"),
            "bid": item.get("l1_bid"),
            "ask": item.get("l1_ask"),
            "bid_size": item.get("l1_bid_size"),
            "ask_size": item.get("l1_ask_size"),
            "l1_quote_time": item.get("l1_quote_time"),
            "l1_quote_serial": item.get("l1_quote_serial"),
            "l1_quote_source": item.get("l1_quote_source"),
        },
        "ranking": {
            "position": item.get("ranking_position"),
            "screening_score": item.get("rank_score"),
            "research_model": dict(item.get("ranking_model") or {}),
        },
        "strategy": {
            "setup": plan.get("setup"),
            "trigger": plan.get("trigger"),
            "max_entry": plan.get("max_entry"),
            "stop": plan.get("stop"),
            "target": plan.get("target"),
            "target_2": plan.get("target_2"),
            "rr": plan.get("rr"),
            "production_eligible": bool(plan.get("production_eligible", False)),
        },
        "risk": risk,
        "monitor": monitor,
        "decision": decision,
        "research_context": {
            "regime": (
                ((item.get("ml") or {}).get("regime") or {}).get("label")
                if isinstance((item.get("ml") or {}).get("regime"), dict)
                else (item.get("ml") or {}).get("regime")
            ),
            "setup": plan.get("setup"),
            "strategy_version": item.get("strategy_version"),
            "model_version": item.get("model_version"),
            "feature_schema_version": item.get("feature_schema_version"),
            "rule_config_version": item.get("rule_config_version"),
        },
        "outcome": dict(item.get("outcome") or {}),
        "classification_cap": item.get("classification_cap"),
        "paper_gate": gate.to_dict(),
        "action": (
            "PAPER_SIMULATION_ELIGIBLE"
            if gate.simulation_allowed and plan
            else "SHADOW_OBSERVE"
        ),
    }


def write_paper_run_file(path, snapshots):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.2",
        "records": list(snapshots or []),
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def upload_paper_run_to_gcs(*, local_path, bucket_name, object_name, client=None):
    if not bucket_name:
        return {"uploaded": False, "reason": "PAPER_GCS_BUCKET 未設定"}

    if client is None:
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("GCS backend 需要 google-cloud-storage") from exc
        client = storage.Client()

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(str(local_path), content_type="application/json")
    return {
        "uploaded": True,
        "bucket": bucket_name,
        "object": object_name,
    }
