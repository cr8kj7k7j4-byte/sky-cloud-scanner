"""Frozen configuration for the daily (隔日方向) backtest.

Sources:
- Cost model: docs/SKY_VALIDATION_PROTOCOL_V1_0.md (Gate 5)
- Risk values: docs/SKY_RISK_PROFILE.md, Amendment A1 (2026-11-22, owner decision).
  The original values (1R 5,000 etc.) are kept in that file for traceability.
"""

# Gate 5: round-trip costs as a fraction of notional.
COST_PRIMARY_ROUND_TRIP = 0.0045
COST_STRESS_ROUND_TRIP = 0.0065

# Risk (Amendment A1).
ONE_R_TWD = 100_000
DAILY_STOP_NEW_ENTRY_TWD = 100_000
PORTFOLIO_HEAT_TWD = 100_000
MAX_SINGLE_NOTIONAL_SWING_TWD = 100_000
MAX_DAY_TRADE_NOTIONAL_TWD = 2_500_000
SHARE_LOT = 1_000

# Universe / liquidity (PREREGISTRATION_V1).
MAX_PRICE = 200.0
MIN_AVG_VOLUME_20D = 1_000_000

# Time splits (PREREGISTRATION_V1). research_test_2026 was already used in prior
# research and is NOT fresh OOS.
SPLITS = {
    "train": ("2025-01-01", "2025-06-30"),
    "validation": ("2025-07-01", "2025-12-31"),
    "research_test_2026": ("2026-01-01", "2026-10-22"),
}
