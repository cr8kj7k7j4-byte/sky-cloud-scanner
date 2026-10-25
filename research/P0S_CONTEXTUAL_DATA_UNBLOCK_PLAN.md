# Contextual P0-S Data Unblock Plan

## Status
DATA ENGINEERING ONLY — NO STRATEGY RETUNING

## 1. VWAP replay
Source: Fugle historical candles `average`.

Verified semantic:
- cumulative transaction average from market open
- usable as session cumulative VWAP context for intraday replay

Required implementation:
- persist `average` at every 5m decision timestamp
- derive `price_vs_vwap_pct`
- no use of future bars

## 2. Effective-dated sector membership
Official source family:
- TWSE industry-category adjustment announcements
- TPEx industry-category adjustment announcements

Required schema:
- symbol
- exchange
- sector
- effective_from
- effective_to
- source_url / source_document
- observed_at

Construction rule:
- start from a dated baseline classification
- apply each official adjustment on its published effective date
- never backfill current membership into earlier dates

Coverage gate:
- >=95% of candidate symbol-date rows must resolve to a contemporaneous sector

## 3. Market-state replay
Required:
- point-in-time index return
- market breadth
- volatility

Do not use half-year hindsight labels.

## 4. Derived Anti-Chase / Phase fields
Allowed from historical OHLCV/VWAP:
- day return
- session position
- rolling volatility
- ATR14
- price extension ATR
- breakout-bar ATR
- stop-distance ATR
- volume ratio / RVOL, with preregistered deterministic definition

Unavailable microstructure fields:
- historical bid/ask spread unless separately sourced

Missing fields remain MISSING; do not impute.

## 5. Execution order
1. Sector mapping builder
2. Market-state replay builder
3. VWAP / ATR / RVOL feature replay
4. Coverage audit
5. Leakage audit
6. Only then run Contextual Breakout v1 OOS

## Gate
No strategy result is computed until all mandatory coverage and leakage gates pass.
