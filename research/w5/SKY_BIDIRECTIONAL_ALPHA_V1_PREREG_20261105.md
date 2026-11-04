# Sky Bidirectional Alpha V1.0 — W5 preregistration (2026-11-05)

Status: INSUFFICIENT_DATA / RESEARCH_ONLY. Not Production; no automatic orders.

## Structural hypothesis
Unlike archived Top100-only velocity and failed False-Reclaim Short E,
investigate independent *bidirectional* intraday forward labels and verified
execution microstructure, with explicit borrow/short eligibility evidence.
Neither opening-retake nor False-Reclaim E parameters may be retuned.
Six idea families (trend, breakout, failed breakout, VWAP reversion,
opening imbalance, verified order-flow imbalance) are hypotheses only.
M2/M3/M5 cannot be backtested as 'new' without distinct independent input
or target structure approved under governance.

## First deliverable
A fail-closed observer that reads TWSE+TPEx official universe and MIS operational
quotes; verifies session/current-trade coverage; outputs directional research
watchlists, never a trade signal. Positive or negative daily changes are only
watchlist grouping; NOT validated alpha, a probability, or a long/short entry.

## Research specification required before backtesting
- PIT universe with delisting/event handling
- Causal 1m and/or true trade/quote/order-book timestamps
- Forward long/short executable labels at preregistered 15/30/60m horizons
- Explicit actual short-sale eligibility, locate and forced-cover constraints
- Short-side tax and cost profile verified separately; primary 0.45% round-trip
  and stress 0.65%, plus realistic spreads, slippage, fills and borrow fees
- Train/validation/new untouched OOS, at least 3 walk-forward folds
- Bull/neutral/bear regimes; ablations; position, correlation, sector risk
- >=200 eligible forward cases, >=20 actual future trading days,
  >=2 regimes, >=95% outcome completeness, <=20% symbol concentration
- W2/W6 research, W0/P0-G promotion review before any formal change

## Fail closed
No price/volume -> no watchlist. No coverage -> no watchlist.
No verified independent intraday structure -> no entry/stop/target/score.
No verified short entitlement -> no actionable short signal.
No after-cost positive expectancy -> no promotion.
No implied claim that engineering deployment validates alpha.

Governance: SKY_SYSTEM_REGISTRY_V2_1.md,
research/RESEARCH_FREEZE_REGISTRY.md,
docs/SKY_VALIDATION_PROTOCOL_V1_0.md.
