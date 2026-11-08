# Four-strategy comparison — proposed pre-registration (2026-11-09)

**Status: PROPOSED / HOLD_PENDING_W0.** This document is a research proposal, not W0 approval, a backtest result, an executable signal, or a Production change. The benchmark definitions below are frozen only upon W0 approval. No retrospective tuning after results are inspected.

## Source-of-truth governance
Read `SKY_SYSTEM_REGISTRY_V2_1.md`, `research/RESEARCH_FREEZE_REGISTRY.md`, and `docs/SKY_VALIDATION_PROTOCOL_V1_0.md` before running. Any `ARCHIVED_NO_RETUNE` family stays archived. Existing 2026 observations are *not* untouched OOS. Preserve all existing Production flows and W1–W7 ownership. Research output must live in a distinct namespace.

## Candidate intake and overlap gate
| ID | Hypothesis / proposed horizon | Governing overlap check | Admission |
|---|---|---|---|
| A | Trend pullback with confirmed recovery, swing 3–20 trading days | Compare to Opening Retest Reclaim D and existing trend / pullback studies; no old rule recycling | HOLD pending structural novelty and W0 preregistration |
| B | Volume-confirmed range breakout, swing 3–20 trading days | P0-S 5m Breakout and Top100 Velocity are ARCHIVED_NO_RETUNE. A mere parameter/timeframe change is not a new hypothesis. | HOLD; reject if no distinct independent data/target/execution mechanism |
| C | Oversold recovery gated by preobservable market regime, swing 3–20 trading days | Weak-Regime Mean-Reversion 5–20D ARCHIVED_NO_RETUNE. Adding market filter alone is not sufficient without W0-documented structural distinction. | HOLD pending structural novelty |
| D | Institutional consecutive net-buying combined with subsequent confirmed momentum, swing 3–20 trading days | Ensure TWSE/TPEx publication time alignment and precise point-in-time feature availability; not intraday use of post-close flows. | HOLD pending timestamp audit and preregistration |

Priority for *feasibility triage*, not a profitability claim: A, D, C, B. No strategy approved for execution.

## Fixed comparator contract (to be specified and approved BEFORE any performance run)
- Universe: TWSE + TPEx historical point-in-time listed universe, alive on decision date; exclude look-ahead/survivorship; decision-time price **strictly below TWD 100**, liquidity/volume/spread/executability gates fixed prospectively.
- Long-only cash swing; research horizon 3–20 trading days. Intraday systems evaluated only in a separate experiment with independent cost and execution contract. Do not use daily OHLC to assume favorable order of stop/target hits.
- Shared account: initial TWD 500,000; at most 3 concurrent names; max TWD 100,000 capital per name; max 1R = TWD 5,000 loss per trade; portfolio open risk <= TWD 15,000; stop new entries at realized intraday net loss >= TWD 10,000 or two consecutive stops. No averaging down, no chase, no auto-order.
- Position sizing: minimum of 5,000 / per-share stop risk, 100,000 / entry price, and portfolio residual risk/capital constraints; round down to valid trade unit. Explicitly account for fees, tax, slippage; do not claim actual fills from bar data.
- Research common cost assumption: 0.45% round trip primary, 0.65% stress. Also report historical user cash cost profile as a separate sensitivity ONLY where applicable; brokerage-specific fee calibration is not complete execution cost.
- A fair matched comparison uses the same date intervals, eligible universe, capital, maximum holding window, cost assumptions, deterministic stop/target collision policy, portfolio risk and re-entry rules. Strategy-specific setups and invalidation stops must be defined ex ante. If trade frequency differs, report both per-trade AND time-normalized portfolio outcomes.
- For each strategy, explicitly freeze all lookbacks, trend/oversold thresholds, market regime rules, institutional consecutive-day counts, entry time, signal publication lag, limit-price policy, stop/target, time exit, ranking, tie-breaks, and missing-data response **before running any test**. All currently remain TBD; do NOT invent calibrated thresholds.
- Partition time chronologically into train, validation, holdout OOS and >=3 walk-forward folds; previously researched 2026 segments cannot be relabeled untouched OOS. Document sample counts, exclusions, instrument corporate actions, timestamps and data source.
- Required output: after-cost expectancy in R and currency, profit factor, maximum drawdown, drawdown duration, number of independent trades, turnover, annualized portfolio return (when valid), win rate, mean win/loss, MAE/MFE, market bull/neutral/bear slices, concentration, sector correlation, fillability/capacity sensitivity, bootstrap uncertainty.
- Gate: integrity and causal timestamps PASS; no overfit to validation/OOS; positive net expectancy and robustness against stress cost, acceptable drawdown, adequate sample size, no market-regime catastrophe; portfolio and execution checks; W0/P0-G decides governance, never automatically promote.

## Meta-labeling research (only after base strategy passes first-stage gates)
- Primary model emits a timestamped candidate with deterministic entry/stop/target and hypothetical execution costs.
- Secondary *binary accept/reject* model is trained using only as-of signal features and **future realized after-cost label** (e.g. positive net-R within predeclared horizon/triple barrier, with collision policy). Label target and event overlap/purging/embargo must be preregistered.
- Compare baseline unchanged vs meta-filtered on the SAME untouched OOS dates, with walk-forward cross-fitted probabilities; tune threshold only on training/validation. Model score/probability is NOT verified win probability absent calibration and reliability evidence.
- Report coverage, selection rate, precision, calibration/Brier if probabilities shown, after-cost portfolio expectancy, PF, DD, lost winners, and confidence intervals. No accuracy-only promotion; do not reanimate archived strategies by ML-only threshold selection.

## Forward evidence
Start *non-tradable research* signal logging only after data integrity and signal contracts pass: model id/version, symbol, market, event timestamp/timezone, data-last-trade and publication times, OHLCV source, feature availability, market regime, entry trigger, accept price, stop/invalidation, two targets, expected cost, candidate reasons, rejected reasons, outcomes and fill-proxy limitations. Unique decision id; no duplicate sample counts.
Minimum for forward consideration: >=200 evaluable independent decisions, >=20 future trading days, >=2 market regimes, >=95% outcome completeness, <=20% single-symbol share; plus after-cost portfolio risk and execution evidence. Shadow/Paper != live P&L.

## Execution acceptance checklist (none claimed complete)
- [ ] W0 approves structural-novelty audit and study preregistration.
- [ ] W3A confirms PIT market + institutional flow availability, timestamps and historic coverage.
- [ ] W1 identifies executable strategy interfaces and freezes exact rules for each admitted candidate.
- [ ] W6 confirms realistic order, spread, slippage and fee/tax conventions.
- [ ] Research runner and deterministic fixtures/tests demonstrate same-universe fairness and no leak.
- [ ] Train/validation/OOS and walk-forward evidence saved with hashes, time range, costs and full metrics.
- [ ] Meta-label experiment runs only on qualifying base candidates with purged/embargoed labels.
- [ ] Forward research ledger and outcome markout validated (distinct from Production).
- [ ] W0/P0-G formally reviews promotion; Production remains unchanged until then.

**Current decision: INSUFFICIENT_DATA / HOLD_PENDING_W0. No qualified new entry, no fabricated price or score.**
