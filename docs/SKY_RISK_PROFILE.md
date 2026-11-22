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

## Amendment A1 — 2026-11-22 (owner decision, pending governance review)

Original values above are kept unchanged for traceability. Per the owner's
instruction on 2026-11-22, the repository follows the following values:

- 1R maximum loss per trade: TWD 100,000 (was 5,000)
- Daily stop-new-entry threshold: TWD 100,000 (was -2R = 10,000)
- Maximum portfolio heat: TWD 100,000 (was 3R = 15,000)
- Day-trade system cap (当沖): TWD 2,500,000 (new)
- Swing / trend single-position notional cap: TWD 100,000 (unchanged; not changed on 2026-11-22)

Known conflicts recorded for the owner:
- Total capital is TWD 500,000 plus financing of TWD 500,000 (buying power about TWD 1,000,000). A TWD 2,500,000 day-trade cap exceeds that unless the broker's day-trade leverage allows it. Broker terms not verified.
- 1R = 100,000 equals 20% of capital. A single stop-out reaches the daily stop threshold. Two-consecutive-stop rule is therefore effectively replaced by the single-stop daily threshold.

Status: applied in repository configuration for research. Not an approval for live trading. Live auto-execution remains DISABLED.
