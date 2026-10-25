from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ComponentCheck:
    name: str
    weight: int
    passed: bool
    detail: str = ""

    def to_dict(self):
        return asdict(self)


def engineering_readiness(checks):
    """
    Returns an engineering-readiness score only.
    It must never be described as win rate, expected return, or trading probability.
    """
    checks = list(checks or [])
    total = sum(max(0, int(c.weight)) for c in checks)
    earned = sum(max(0, int(c.weight)) for c in checks if c.passed)
    score = round(100.0 * earned / total, 1) if total else 0.0

    blocking = [c.name for c in checks if not c.passed]
    return {
        "score": score,
        "meaning": "工程成熟度，不代表投資績效或獲利機率",
        "production_ready": len(blocking) == 0,
        "blocking_components": blocking,
        "checks": [c.to_dict() for c in checks],
    }


def default_sky100_checks(
    *,
    official_data_chain=False,
    feature_contract=False,
    knowledge_engine=False,
    decision_engine=False,
    ranking_engine=False,
    risk_engine=False,
    position_manager=False,
    trade_logging=False,
    walk_forward=False,
    oos=False,
    cost_stress=False,
    leakage_check=False,
    paper_trade=False,
    monitoring=False,
):
    return [
        ComponentCheck("官方資料鏈", 12, official_data_chain),
        ComponentCheck("Feature Contract", 8, feature_contract),
        ComponentCheck("P0-K Knowledge/Evidence", 8, knowledge_engine),
        ComponentCheck("P0-C Decision Engine", 10, decision_engine),
        ComponentCheck("P0-O Ranking Engine", 8, ranking_engine),
        ComponentCheck("P0-R Risk Engine", 12, risk_engine),
        ComponentCheck("PMS Position Manager", 8, position_manager),
        ComponentCheck("交易紀錄/MFE/MAE/R", 8, trade_logging),
        ComponentCheck("Walk-forward", 10, walk_forward),
        ComponentCheck("OOS", 10, oos),
        ComponentCheck("成本壓力測試", 8, cost_stress),
        ComponentCheck("資料洩漏檢查", 8, leakage_check),
        ComponentCheck("Paper Trading", 8, paper_trade),
        ComponentCheck("監控與告警", 6, monitoring),
    ]
