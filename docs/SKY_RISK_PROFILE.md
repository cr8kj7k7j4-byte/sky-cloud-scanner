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

## Paper-only research without a brokerage account

- Opening a brokerage account is **NOT** a prerequisite for P0-R research, offline tests, Shadow observations, or PAPER_ONLY simulation.
- Replace the previous live-holdings acceptance blocker with a **verifiable paper portfolio ledger**: simulated positions, original stops, realized daily simulated net PnL, open risk, and consecutive simulated stops.
- Missing/mismatched simulated ledger data must fail closed. It is not valid to assume zero positions or zero daily loss.
- A paper portfolio is never a real portfolio; paper fills, realized PnL, and execution assumptions must be labeled simulation.
- The Fugle market-data API does not need broker-account authorization for this research gate.
- Real order execution and brokerage ledger integrations are outside the present scope and remain disabled.

## P0-R research acceptance — explicit broker-independent gate (2026-11-11)

- **Removed mandatory prerequisite:** proving that a real brokerage account, order API, holdings API, or trade/fill history API exists or can be authorized. The user has no brokerage account; do not request opening one for research acceptance.
- **Required instead:** a traceable `PAPER_ONLY` simulated ledger with timestamped portfolio snapshots, position and original-stop provenance, simulated orders/fills and non-fills, execution assumptions, realized *simulated* daily net PnL, consecutive simulated stop count, open risk and audit-readable artifacts.
- All simulated fills must be distinguished from market observations. Apply full modeled fees, taxes, spread, slippage, liquidity and fill assumptions; missing or inconsistent simulation evidence fails closed.
- Enforce existing P0-R capital, per-trade risk, notional, concurrent position, portfolio heat, daily stop, two-loss lock and execution-adjusted RR constraints unchanged.
- Gate result is **RESEARCH/PAPER_ONLY only**; no inference of real fill quality, real PnL or Production readiness. `LIVE_TRADING_ENABLED=false` / no real broker order endpoint remains a hard invariant.
- Real broker integration and Small Live are **deferred, optional future scopes** needing separate explicit authorization; they are not blockers for P0-R research/Shadow/Paper verification. Existing strategy promotion, W0/P0-G, data and CI/Artifact gates remain in force.
