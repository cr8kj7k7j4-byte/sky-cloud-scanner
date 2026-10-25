# Sky P0-S Contextual Breakout v1 — Data Availability Audit

## Status
**DATA_BLOCKED / DO NOT BACKTEST YET**

## Date
2026-10-25

## Scope
Audit whether the repository can reconstruct the preregistered point-in-time context required by:

Market Regime → Sector RS → Phase / Anti-Chase → 5m Setup / Trigger

No strategy parameter was changed in this audit.

## Historical 5m base data
The current expanded downloader persists:
- open
- high
- low
- close
- volume
- average

This is sufficient for the frozen 5m breakout mechanics and for some derived price/volume features.

It is not sufficient by itself to satisfy the full contextual preregistration.

## 1. Market Regime

### Required
- market/index return at decision time
- market breadth
- volatility
- regime label

### Repository status
- `src/regime_engine.py` can classify a regime when index_change_pct / breadth_pct / volatility_pct are supplied.
- The current historical 5m export does not persist a synchronized historical market index + full-market breadth series for every candidate decision timestamp.

### Decision
**DATA BLOCKED for full point-in-time replay.**

Do not substitute current market state, half-year labels, or future summary statistics.

## 2. Sector Relative Strength

### Required
- historical sector membership with effective_from / effective_to
- stock lookback return
- sector lookback return
- sector RS vs market
- stock RS vs sector

### Repository status
- `src/sector_rs_replay.py` correctly requires point-in-time mapping rows.
- No canonical historical stock-sector mapping with effective_from/effective_to is currently present in the repository.
- `src/global_sector_mapping.py` is a current global-context-to-sector background mapper; it is not a historical stock membership table.

### Decision
**DATA BLOCKED.**

Sector RS must not be claimed or backfilled using current-only membership.

## 3. Phase / Anti-Chase

### Potentially derivable from current 5m OHLCV
- intraday return
- bar range
- rolling volatility
- simple volume ratios
- session high/low position
- some momentum measures

### Requires semantic verification / new replay logic
- VWAP from historical `average`
- RVOL definition
- ATR14 / price extension ATR
- breakout-bar ATR
- stop-distance ATR
- phase classification

### Not present in current historical export
- spread / bid-ask history
- explicit resistance distance
- verified historical phase label

### Decision
**PARTIAL DATA ONLY — insufficient for the preregistered composite Anti-Chase / Phase gate.**

Do not fabricate spread, resistance, phase, ATR, or VWAP semantics.

## 4. Full Contextual Breakout v1

The preregistered combined candidate cannot currently be executed without violating point-in-time / leakage rules.

### Blockers
1. historical market breadth/index replay at decision timestamps
2. historical effective-dated sector membership
3. verified Sector RS replay inputs
4. complete Anti-Chase / Phase replay fields
5. semantic verification of historical `average` before treating it as VWAP

## Allowed next work

Only data-infrastructure work is allowed before the backtest:

1. Build a point-in-time market-state replay table.
2. Build an effective-dated stock-sector membership table.
3. Verify the historical `average` field semantics.
4. Define deterministic ATR / RVOL / Phase calculations using only prior/current data.
5. Record unavailable microstructure fields such as spread as MISSING rather than imputing.
6. Measure coverage before any strategy result is computed.

## Coverage gates

Before the full study may start:
- Market context coverage >= 95%
- Sector membership coverage >= 95%
- Sector RS price coverage >= 95%
- Required Anti-Chase / Phase core-field coverage >= 95%
- Leakage audit = PASS

If any mandatory gate fails, status remains DATA_BLOCKED.

## Governance decision
**Do not run Contextual Breakout v1 yet.**

This is a data problem, not a strategy-tuning problem.
