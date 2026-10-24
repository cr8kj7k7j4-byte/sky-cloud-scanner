# Sky V2.1 Execution-adjusted RR Contract

- Date: 2026-10-24
- Module: P0-X Execution Engine
- Status: RESEARCH / INFRASTRUCTURE
- Production gate: DISABLED BY DEFAULT

## Problem found

The existing P0-R `risk_engine.py` field named `net_rr` is calculated as:

`(target - entry) / (entry - stop)`

That is a **Gross RR**, not a cost-adjusted RR.

For backward compatibility the old field may temporarily remain, but new code must distinguish:

1. **Gross RR**
2. **Fee/Tax-adjusted RR**
3. **Execution-adjusted RR**
4. **Fill-adjusted expected RR (research heuristic)**

## Calculation layers

### Gross RR

Pure price geometry:

`gross_reward / gross_risk`

### Fee/Tax-adjusted RR

Explicit:
- buy commission
- sell commission
- sell-side transaction tax

No rate is silently assumed. Missing input returns `None`.

### Execution-adjusted RR

Adds:
- entry adverse slippage
- exit adverse slippage
- half-spread on entry
- half-spread on exit
- liquidity penalty

Effective long entry is worsened upward.
Effective exits are worsened downward.

The denominator also includes cost on a stop-loss exit, so the model does not understate downside risk.

### Fill-adjusted expected RR

`execution_adjusted_rr * fill_probability`

This is a **research heuristic**, not a true statistical Expectancy and not a win probability.

## Governance

- Missing cost assumptions are NEVER converted to zero.
- Zero is valid only when explicitly configured.
- Production RR gate is disabled by default.
- Gate may be enabled only after broker/account-specific fee/tax assumptions and empirical slippage/spread distributions are supplied.
- Cost model must be versioned in P0-G.

## Required runtime assumptions

- buy_commission_rate
- sell_commission_rate
- sell_tax_rate
- entry_slippage_bps
- exit_slippage_bps
- spread_bps
- liquidity_penalty_bps
- optional fill_probability

## Planned ablation

For every historical signal:

1. Gross RR
2. Fee/Tax RR
3. Execution-adjusted RR
4. Observed cost-adjusted outcome
5. Realized slippage when available

Compare thresholds:
- >= 1.0
- >= 1.25
- >= 1.5
- >= 1.75
- >= 2.0
- >= 2.5

Metrics:
- trade count
- Net Expectancy
- PF
- MDD
- tail loss
- turnover
- cost drag
- yearly stability
- 2024+ OOS proxy
- Market Regime stratification

## Current conclusion

Sky must stop calling price-only RR "net_rr".

The P0-X engine can now compute a real execution-adjusted RR, but it cannot produce an honest value until explicit cost assumptions are supplied.

**Status: ENGINE READY — PRODUCTION COST ASSUMPTIONS REQUIRED**
