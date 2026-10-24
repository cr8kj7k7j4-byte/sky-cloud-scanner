from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from .execution_engine import ExecutionCostPolicy


@dataclass(frozen=True)
class ObservedCostProfile:
    profile_id: str
    label_zh: str
    transaction_mode: str
    buy_commission_rate: float
    sell_commission_rate: float
    sell_tax_rate: float
    observed_samples: int
    evidence_date: str
    evidence_note: str
    financing_interest_mode: str = "NOT_APPLICABLE"
    observed_financing_interest_twd: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_execution_policy(
        self,
        *,
        entry_slippage_bps=None,
        exit_slippage_bps=None,
        spread_bps=None,
        liquidity_penalty_bps=None,
        fill_probability=None,
        financing_interest_per_share=None,
        min_execution_rr=1.5,
        enforce_gate=False,
    ) -> ExecutionCostPolicy:
        return ExecutionCostPolicy(
            buy_commission_rate=self.buy_commission_rate,
            sell_commission_rate=self.sell_commission_rate,
            sell_tax_rate=self.sell_tax_rate,
            entry_slippage_bps=entry_slippage_bps,
            exit_slippage_bps=exit_slippage_bps,
            spread_bps=spread_bps,
            liquidity_penalty_bps=liquidity_penalty_bps,
            fill_probability=fill_probability,
            financing_interest_per_share=financing_interest_per_share,
            require_financing_interest=(self.transaction_mode == "MARGIN_FINANCING"),
            min_execution_rr=min_execution_rr,
            enforce_gate=enforce_gate,
        )


# Empirical center from the user's brokerage statements.
# Fee legs observed: 12 / 36,050 ; 12 / 35,900 ; 12 / 37,050 ; 12 / 35,900.
# Because statement fees are rounded to integer TWD, 0.000333 is used as a
# stable central calibration rather than overfitting to each rounded leg.
_USER_COMMISSION_RATE = 0.000333


USER_CASH_DAYTRADE_20261022 = ObservedCostProfile(
    profile_id="USER_CASH_DAYTRADE_20261022",
    label_zh="使用者實證｜現股當沖",
    transaction_mode="CASH_DAYTRADE",
    buy_commission_rate=_USER_COMMISSION_RATE,
    sell_commission_rate=_USER_COMMISSION_RATE,
    sell_tax_rate=0.0015,
    observed_samples=1,
    evidence_date="2026-10-22",
    evidence_note=(
        "2409 友達 1,000股：買36.05、賣35.90；"
        "買進手續費12元、賣出手續費12元、交易稅53元；"
        "純價差-150元，實現損益-227元。"
    ),
)


USER_MARGIN_FINANCING_20261021 = ObservedCostProfile(
    profile_id="USER_MARGIN_FINANCING_20261021",
    label_zh="使用者實證｜融資交易",
    transaction_mode="MARGIN_FINANCING",
    buy_commission_rate=_USER_COMMISSION_RATE,
    sell_commission_rate=_USER_COMMISSION_RATE,
    sell_tax_rate=0.0030,
    observed_samples=1,
    evidence_date="2026-10-21",
    evidence_note=(
        "2409 友達 1,000股：買37.05、賣35.90；"
        "買進手續費12元、賣出手續費12元、交易稅107元、利息13元；"
        "純價差-1,150元，實現損益-1,294元。"
    ),
    financing_interest_mode="PER_TRADE_OR_HOLDING_PERIOD_INPUT_REQUIRED",
    observed_financing_interest_twd=13.0,
)


PROFILES = {
    USER_CASH_DAYTRADE_20261022.profile_id: USER_CASH_DAYTRADE_20261022,
    USER_MARGIN_FINANCING_20261021.profile_id: USER_MARGIN_FINANCING_20261021,
}


def get_observed_cost_profile(profile_id: str | None) -> ObservedCostProfile | None:
    if not profile_id:
        return None
    return PROFILES.get(str(profile_id).strip())


def list_observed_cost_profiles() -> list[dict]:
    return [p.to_dict() for p in PROFILES.values()]
