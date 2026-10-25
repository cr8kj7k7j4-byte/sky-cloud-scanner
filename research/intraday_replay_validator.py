from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


CANONICAL_RULE_COLUMNS = [
    "market_gate",
    "sector_rs_gate",
    "multi_timeframe_gate",
    "phase_gate",
    "setup_gate",
    "trigger_gate",
    "anti_chase_gate",
    "rr_gate",
    "opportunity_ranking_gate",
    "execution_adjustment_gate",
]

IDENTITY_COLUMNS = [
    "decision_id",
    "run_id",
    "strategy_id",
    "strategy_version",
    "symbol",
    "exchange",
    "session_date",
    "observation_timestamp",
    "feature_cutoff_timestamp",
    "decision_timestamp",
    "data_timezone",
    "feature_schema_version",
    "rule_schema_version",
    "cost_model_version",
]

GOVERNANCE_COLUMNS = [
    "pit_universe_member",
    "data_quality_status",
    "leakage_audit_status",
    "market_context_status",
    "sector_mapping_status",
    "execution_context_status",
    "replay_coverage_status",
]

OUTCOME_COLUMNS = [
    "net_r_045",
    "net_r_065",
]

CORE_CONTEXT_GROUPS = {
    "market_context": [
        "market_regime",
        "market_return",
        "market_breadth",
        "market_volatility",
    ],
    "sector_context": [
        "sector",
        "sector_return",
        "sector_rs_vs_market",
        "stock_rs_vs_sector",
    ],
    "anti_chase_phase": [
        "cumulative_vwap",
        "price_vs_vwap_pct",
        "atr14",
        "price_extension_atr",
        "rvol",
        "session_position",
        "stop_distance_pct",
        "phase",
    ],
    "ranking_context": [
        "candidate_pool_id",
        "candidate_pool_size",
        "rank_score",
        "ranking_position",
        "ranking_decile",
        "ranking_model_version",
    ],
    "execution_context": [
        "planned_entry",
        "planned_stop",
        "planned_target_1",
        "gross_rr",
        "execution_adjusted_rr",
    ],
}


@dataclass(frozen=True)
class CoverageThresholds:
    mandatory: float = 0.95
    outcome: float = 0.95
    cost: float = 1.0


def _coverage(df: pd.DataFrame, columns: Iterable[str]) -> float:
    cols = [c for c in columns if c in df.columns]
    if not cols or df.empty:
        return 0.0
    return float(df[cols].notna().all(axis=1).mean())


def _status_coverage(df: pd.DataFrame, column: str, accepted=("OK", "PASS")) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    values = df[column].astype(str).str.upper()
    return float(values.isin({x.upper() for x in accepted}).mean())


def _timestamp_causality(df: pd.DataFrame) -> tuple[float, int]:
    needed = {"feature_cutoff_timestamp", "decision_timestamp"}
    if not needed.issubset(df.columns) or df.empty:
        return 0.0, len(df)
    feature_ts = pd.to_datetime(df["feature_cutoff_timestamp"], errors="coerce", utc=True)
    decision_ts = pd.to_datetime(df["decision_timestamp"], errors="coerce", utc=True)
    valid = feature_ts.notna() & decision_ts.notna() & (feature_ts <= decision_ts)
    return float(valid.mean()), int((~valid).sum())


def _bool_column_validity(df: pd.DataFrame, columns: Iterable[str]) -> dict:
    out = {}
    accepted = {"true", "false", "1", "0"}
    for col in columns:
        if col not in df.columns:
            out[col] = {"present": False, "valid_share": 0.0}
            continue
        s = df[col]
        valid = s.map(
            lambda x: (
                isinstance(x, (bool, int))
                and (not isinstance(x, int) or x in (0, 1))
            )
            or str(x).strip().lower() in accepted
        )
        valid_share = float(valid.mean()) if len(valid) else 0.0
        out[col] = {"present": True, "valid_share": valid_share}
    return out


def validate_replay_frame(
    df: pd.DataFrame,
    *,
    thresholds: CoverageThresholds | None = None,
    require_sector: bool = True,
) -> dict:
    thresholds = thresholds or CoverageThresholds()
    missing_identity = sorted(set(IDENTITY_COLUMNS) - set(df.columns))
    missing_rules = sorted(set(CANONICAL_RULE_COLUMNS) - set(df.columns))
    missing_governance = sorted(set(GOVERNANCE_COLUMNS) - set(df.columns))
    missing_outcomes = sorted(set(OUTCOME_COLUMNS) - set(df.columns))

    reasons: list[str] = []
    if df.empty:
        reasons.append("EMPTY_DATASET")
    if missing_identity:
        reasons.append("MISSING_IDENTITY_COLUMNS")
    if missing_rules:
        reasons.append("MISSING_CANONICAL_RULE_COLUMNS")
    if missing_governance:
        reasons.append("MISSING_GOVERNANCE_COLUMNS")
    if missing_outcomes:
        reasons.append("MISSING_COST_OUTCOME_COLUMNS")

    timestamp_coverage, timestamp_violations = _timestamp_causality(df)
    if timestamp_coverage < 1.0 or timestamp_violations > 0:
        reasons.append("TIMESTAMP_CAUSALITY_FAIL")

    pit_coverage = (
        float(pd.to_numeric(df["pit_universe_member"], errors="coerce").fillna(0).astype(bool).mean())
        if "pit_universe_member" in df.columns and not df.empty
        else 0.0
    )
    leakage_pass = _status_coverage(df, "leakage_audit_status", accepted=("PASS",))
    data_quality_status = _status_coverage(df, "data_quality_status", accepted=("OK", "PASS"))
    market_status = _status_coverage(df, "market_context_status", accepted=("OK",))
    sector_status = _status_coverage(df, "sector_mapping_status", accepted=("OK",))
    execution_status = _status_coverage(df, "execution_context_status", accepted=("OK",))
    replay_status = _status_coverage(df, "replay_coverage_status", accepted=("OK",))

    group_coverage = {
        name: _coverage(df, columns)
        for name, columns in CORE_CONTEXT_GROUPS.items()
    }

    if pit_coverage < thresholds.mandatory:
        reasons.append("PIT_UNIVERSE_COVERAGE_FAIL")
    if data_quality_status < thresholds.mandatory:
        reasons.append("DATA_QUALITY_COVERAGE_FAIL")
    if leakage_pass < 1.0:
        reasons.append("LEAKAGE_AUDIT_NOT_FULL_PASS")
    if market_status < thresholds.mandatory:
        reasons.append("MARKET_CONTEXT_COVERAGE_FAIL")
    if require_sector and sector_status < thresholds.mandatory:
        reasons.append("SECTOR_MAPPING_COVERAGE_FAIL")
    if execution_status < thresholds.mandatory:
        reasons.append("EXECUTION_CONTEXT_COVERAGE_FAIL")
    if replay_status < thresholds.mandatory:
        reasons.append("REPLAY_STATUS_COVERAGE_FAIL")

    for name, coverage in group_coverage.items():
        if name == "sector_context" and not require_sector:
            continue
        if coverage < thresholds.mandatory:
            reasons.append(f"{name.upper()}_COVERAGE_FAIL")

    outcome_coverage = {
        col: (float(df[col].notna().mean()) if col in df.columns and not df.empty else 0.0)
        for col in OUTCOME_COLUMNS
    }
    if any(v < thresholds.outcome for v in outcome_coverage.values()):
        reasons.append("OUTCOME_COMPLETENESS_FAIL")
    if any(v < thresholds.cost for v in outcome_coverage.values()):
        reasons.append("COST_MODEL_COMPLETENESS_FAIL")

    duplicated_decisions = (
        int(df["decision_id"].duplicated().sum())
        if "decision_id" in df.columns
        else len(df)
    )
    if duplicated_decisions:
        reasons.append("DUPLICATE_DECISION_ID")

    rule_validity = _bool_column_validity(df, CANONICAL_RULE_COLUMNS)
    invalid_rules = [
        k for k, v in rule_validity.items()
        if not v["present"] or v["valid_share"] < 1.0
    ]
    if invalid_rules:
        reasons.append("INVALID_RULE_COLUMNS")

    unique_reasons = sorted(set(reasons))
    gate = "PASS" if not unique_reasons else "DATA_BLOCKED"

    return {
        "gate": gate,
        "row_count": int(len(df)),
        "missing_identity_columns": missing_identity,
        "missing_rule_columns": missing_rules,
        "missing_governance_columns": missing_governance,
        "missing_outcome_columns": missing_outcomes,
        "timestamp_causality_coverage": round(timestamp_coverage, 6),
        "timestamp_causality_violations": timestamp_violations,
        "pit_universe_coverage": round(pit_coverage, 6),
        "data_quality_ok_share": round(data_quality_status, 6),
        "leakage_pass_share": round(leakage_pass, 6),
        "market_context_ok_share": round(market_status, 6),
        "sector_mapping_ok_share": round(sector_status, 6),
        "execution_context_ok_share": round(execution_status, 6),
        "replay_coverage_ok_share": round(replay_status, 6),
        "context_coverage": {k: round(v, 6) for k, v in group_coverage.items()},
        "outcome_coverage": {k: round(v, 6) for k, v in outcome_coverage.items()},
        "duplicate_decision_ids": duplicated_decisions,
        "rule_validity": rule_validity,
        "reasons": unique_reasons,
        "production_eligible": False,
        "note": (
            "PASS means the replay dataset meets the W2 research data contract. "
            "It does not authorize Production promotion."
        ),
    }
