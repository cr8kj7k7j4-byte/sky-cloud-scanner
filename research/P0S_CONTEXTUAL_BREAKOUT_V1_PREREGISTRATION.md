# Sky P0-S Contextual Breakout v1 — Pre-registration

## Status
**PRE-REGISTERED / DATA-GATED / NOT PRODUCTION**

## Date
2026-10-25

## Research question
Can the previously rejected naked 5-minute breakout become a valid candidate only when conditioned on independent, point-in-time context that already exists in Sky's architecture?

This is a structural successor, not a retune of the rejected naked breakout.

## Fixed architecture
Decision chain under test:

Market Regime → Sector Relative Strength → Phase / Anti-Chase → 5m Setup / Trigger

The 5m breakout remains the execution setup. The hypothesis is that context filters may identify a materially different subset of trades.

## Frozen baseline setup
No changes are allowed to the archived naked breakout mechanics in this candidate:

- prior lookback = 4 x 5m bars
- trigger = highest high of prior 4 bars
- stop = lowest low of prior 4 bars
- target = 2.0R
- max acceptable entry = Trigger + 0.25R
- risk bounds = 0.30%–2.50%
- max hold = 24 x 5m bars
- same-bar stop/target ambiguity = stop-first
- primary round-trip cost = 0.45%

These values are frozen so any improvement must come from independent contextual evidence, not parameter rescue.

## Required point-in-time features

### Market Regime
Required at decision time:
- index return / market trend inputs
- market breadth
- volatility
- regime label

No future half-year summary or future returns may be used.

### Sector Relative Strength
Required at decision time:
- time-aware sector membership
- sector lookback return
- stock lookback return
- sector RS vs market
- stock RS vs sector

Coverage gate:
- sector mapping coverage >= 95%
- price-history coverage >= 95%

If this gate is not met, Sector RS analysis remains DATA BLOCKED.

### Phase / Anti-Chase
Required at decision time where available:
- price vs VWAP
- VWAP slope
- day return
- gap
- ATR14
- price extension in ATR
- breakout-bar ATR
- RVOL / volume z-score
- resistance distance
- stop distance %
- stop distance ATR
- spread
- phase label

No future MFE / MAE / exit outcome may be used to construct these fields.

## Candidate comparisons
The study will compare only pre-declared variants:

1. Naked breakout baseline
2. + Market Regime
3. + Sector RS
4. + Market Regime + Sector RS
5. + Market Regime + Phase / Anti-Chase
6. + Market Regime + Sector RS + Phase / Anti-Chase

No post-result threshold mining is allowed.

## Market Regime handling
Existing production-like `regime_engine.py` output may be replayed only if its input fields are available point-in-time.

No research threshold from historical half-year analysis is promoted automatically.

## Sector RS handling
Sector RS is not a hard gate until point-in-time coverage reaches the preregistered coverage gate.

No use of current sector membership to backfill historical membership.

## Anti-Chase handling
The rejected standalone trigger-slip proxy must not be reused as a hard veto.

Composite Anti-Chase may only use contemporaneous structural fields listed above.

## Primary evaluation
Primary OOS metrics:
- trade count
- after-cost Expectancy R
- PF
- win rate
- MFE / MAE
- max drawdown
- tail-loss frequency
- yearly stability
- regime stability

## Minimum promotion gate
A candidate may advance only if all are true:

- OOS n >= 300
- after-cost Expectancy R > 0
- PF >= 1.20
- no single calendar year contributes > 50% of total positive expectancy
- no tested major regime has materially negative expectancy without a documented risk-off rule
- data coverage gates pass
- leakage audit passes
- improvement versus naked baseline survives walk-forward
- result survives 0.65% cost stress with Expectancy >= 0
- no parameter was changed after reviewing OOS results

Passing this gate authorizes only Paper / Shadow validation, not Production.

## Automatic rejection
Reject / archive this candidate if any of the following occurs:

- zero-cost Expectancy <= 0 after the contextual gates
- primary-cost PF < 1.0
- OOS n < 300 after filtering
- point-in-time Sector RS coverage < 95% when Sector RS is claimed
- evidence relies on future outcomes or current-only sector mapping
- positive result is dominated by one year / one narrow subgroup
- improvement disappears in walk-forward or cost stress

## Forbidden rescue actions
After results are seen, do not:
- tune Market thresholds
- tune Sector RS percentile cutoffs
- tune target R / stop / lookback / max-entry
- change cost assumption to obtain a pass
- switch to RF/XGBoost/LightGBM to rescue a failed deterministic hypothesis
- cherry-pick years, sectors, or time windows

Any materially new design requires a new preregistration.

## Production guardrail
No Production behavior changes.
No A+ promotion.
No live execution.
No Paper Trading until this preregistered study passes OOS and governance review.

## Next execution gate
Before running the full study, verify whether the repository can reconstruct:
1. point-in-time sector membership,
2. point-in-time Sector RS features,
3. point-in-time Anti-Chase / Phase fields,
for the same historical 5m universe.

If these fields are incomplete, record DATA BLOCKED and do not fabricate or impute them.
