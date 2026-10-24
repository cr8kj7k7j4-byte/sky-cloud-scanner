from __future__ import annotations

ACTION_ZH={
    "BUY":"買進",
    "WAIT":"等待",
    "WATCH":"觀察",
    "HOLD":"續抱",
    "ADD":"加碼",
    "REDUCE":"減碼",
    "STOP":"停損",
    "EXIT":"退出",
    "BLOCK":"禁止交易",
}

def explain_decision(record):
    r=dict(record or {})
    blocked=list(r.get("blocked_gates") or [])
    passed=list(r.get("passed_gates") or [])
    action=str(r.get("action") or "WATCH")
    status=str(r.get("decision_status") or "UNKNOWN")

    if blocked:
        primary=f"主要否決：{blocked[0]}"
    elif passed:
        primary=f"主要依據：{passed[-1]}"
    else:
        primary="主要依據：尚無足夠 Gate 證據"

    return {
        "symbol":r.get("symbol"),
        "action":ACTION_ZH.get(action,action),
        "decision_status":status,
        "primary_reason":primary,
        "passed_gates":passed,
        "blocked_gates":blocked,
        "risk_status":r.get("risk_status"),
        "execution_status":r.get("execution_status"),
        "evidence_ids":list(r.get("evidence_ids") or []),
        "versions":{
            "strategy":r.get("strategy_version"),
            "model":r.get("model_version"),
            "feature_schema":r.get("feature_schema_version"),
            "rule_config":r.get("rule_config_version"),
        },
        "rationale":r.get("rationale"),
        "note":"Explanation is traceability metadata, not a guarantee of correctness or profitability.",
    }
