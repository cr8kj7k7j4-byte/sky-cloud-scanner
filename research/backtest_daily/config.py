"""Frozen configuration for the daily (隔日方向) backtest framework.

Sources:
- Cost model: docs/SKY_VALIDATION_PROTOCOL_V1_0.md (Gate 5)
- Risk capacity: docs/SKY_RISK_PROFILE.md (effective 2026-10-27)

NOTE: The 2026-11-22 owner discussion proposed 1R = 100,000 and a daily
loss cap of 100,000. Those values are NOT applied here because the
authoritative risk profile still says 1R = 5,000. Changing them requires
a dated governance update to docs/SKY_RISK_PROFILE.md.
"""

# Gate 5: primary and stress round-trip costs (fraction of notional).
COST_PRIMARY_ROUND_TRIP = 0.0045
COST_STRESS_ROUND_TRIP = 0.0065

# Risk profile (docs/SKY_RISK_PROFILE.md).
ONE_R_TWD = 5_000
MAX_SINGLE_NOTIONAL_TWD = 100_000
MAX_CONCURRENT_POSITIONS = 3
PORTFOLIO_HEAT_CAP_R = 3
DAILY_STOP_NEW_ENTRY_R = -2
SHARE_LOT = 1_000

# Time splits. 2026 data up to 2026-10-22 was already used as research
# test in prior work, so it is NOT fresh OOS (see research/RESEARCH_FREEZE_REGISTRY.md).
SPLITS = {
    "train": ("2025-01-01", "2025-06-30"),
    "validation": ("2025-07-01", "2025-12-31"),
    "research_test_2026": ("2026-01-01", "2026-10-22"),
}
