# Sky Risk Profile

- Effective date: 2026-10-27
- Scope: P0-R Risk & Portfolio Engine
- Live auto-execution: DISABLED

## User-authorized capital profile

- Total trading capital: TWD 500,000
- 1R maximum loss per trade: TWD 5,000
- Risk per trade: 1.00%
- Maximum single-position notional: 20% = TWD 100,000
- Maximum concurrent positions: 3
- Maximum portfolio heat: 3R = TWD 15,000 = 3.00%
- Daily stop-new-entry threshold: -2R = TWD 10,000 = 2.00%

## Position sizing rule

Recommended shares are constrained by both:
1. 1R risk budget / per-share stop distance
2. TWD 100,000 maximum single-position notional

Taiwan standard lot size remains 1,000 shares unless instrument rules differ.

## Hard risk rules

- No averaging down.
- No loss-position add.
- Stop may only move toward lower risk.
- Two consecutive stop losses OR daily net loss reaching -2R => no further new entries that trading day.
- Maximum concurrent positions = 3.
- Portfolio heat must not exceed 3R.
- Position sizing is advisory only; no automatic order placement is authorized.

## Governance

This profile configures risk capacity only. It does not authorize a candidate strategy, does not change Alpha logic, and does not imply profitability.
