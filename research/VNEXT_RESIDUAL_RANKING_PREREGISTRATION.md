# Sky VNext Pre-registration｜Residual / Market-Neutral Cross-sectional Ranking

## Governance status
**PRE-REGISTERED / RESEARCH_ONLY**

This document freezes the first VNext research design before results are observed.
No production behavior changes are authorized by this preregistration.

## Research question

Can cross-sectional features identify stocks that outperform a market benchmark
over 3D / 5D / 10D horizons after costs and portfolio constraints?

The target is **residual return**, not raw future return.

## Primary labels

For stock i on date t:

- Residual3D = StockReturn3D - MarketBenchmarkReturn3D
- Residual5D = StockReturn5D - MarketBenchmarkReturn5D
- Residual10D = StockReturn10D - MarketBenchmarkReturn10D

Industry/sector residualization may be added only after a point-in-time sector
mapping passes P0-DATA verification. It must not be backfilled with current
sector membership and called historical PIT.

## Universe

- Use the broadest available point-in-time TWSE/TPEx universe that passes the
  current P0-DATA contract.
- Do not substitute a current-listing-only universe without explicitly labeling
  survivorship bias.
- Price/liquidity filters must be pre-declared and applied point-in-time.

## Baseline hierarchy

Run in this order:

1. Deterministic rank baseline.
2. Linear cross-sectional baseline.
3. Random Forest challenger.
4. XGBoost challenger.
5. LightGBM challenger.

Do not run LSTM, Transformer, or RL in this research lane.

## Candidate feature families

Allowed initial families:
- Relative strength / momentum
- Market regime context
- Volatility
- Liquidity
- Abnormal volume
- Sector relative strength, only when PIT-safe
- Revenue evidence, only when PIT-safe
- Event/catalyst evidence as context only

Forbidden shortcuts:
- Future information
- Post-event knowledge not available at decision time
- Current sector/listing metadata backfilled into historical dates
- Target-derived features
- MFE/MAE-derived predictors

## Data splits

Current previously-used 2026 data is not fresh untouched OOS.

The initial study must separate:
- Train
- Validation
- Research Test

A **new future period not used for feature/model selection** is required before
any claim of truly fresh OOS promotion evidence.

No threshold or feature-family change may use Research Test performance to
improve the same candidate.

## Portfolio construction

The research must evaluate deployability, not only signal IC.

Required portfolio tests:
- Daily Top-N: at minimum Top3 / Top5 / Top10
- Maximum concurrent positions
- Symbol concentration
- Sector concentration when sector PIT is available
- Turnover
- Capacity / liquidity constraints
- Correlation / portfolio heat where data is available

## Cost model

At minimum:
- 0.45% primary round-trip stress
- 0.65% higher stress case
- Additional explicit slippage / spread / liquidity-impact assumptions when
  available

Unknown execution inputs must remain UNKNOWN and must not silently become zero.

## Primary evaluation metrics

Signal / ranking:
- Rank IC or cross-sectional monotonicity
- Top-N residual return
- Stability across time splits

Portfolio:
- After-cost Expectancy
- Profit Factor
- Max Drawdown
- Turnover
- Concentration
- Capacity
- Regime stability

Win rate is secondary and cannot independently justify promotion.

## Promotion gates

A candidate advances only if ALL apply:

1. PIT alignment passes.
2. Leakage / survivorship review passes.
3. Pre-registration integrity is preserved.
4. Validation positive after costs.
5. Research Test positive after costs.
6. Walk-forward remains directionally stable.
7. 0.45% cost passes.
8. 0.65% stress remains acceptable.
9. Portfolio implementation preserves positive expectancy.
10. No catastrophic year/regime failure.
11. No excessive single-symbol/sector concentration.
12. Shadow Sample Sufficiency passes.
13. Paper/Shadow outcome evidence passes.
14. P0-G Promotion Scorecard reaches governance-review readiness.
15. Explicit Champion Configuration approval occurs.

## Automatic rejection / archive rules

Archive the candidate family without local retuning when:
- Validation and Research Test are both materially negative after costs; or
- Portfolio implementation destroys the signal-level edge; or
- Results rely on one year, one symbol, one sector, or one tiny subgroup; or
- Leakage/PIT integrity cannot be repaired without changing the research
  question.

A rejected VNext variant may only be reopened with a structural change in
label/data/horizon/execution architecture and a new preregistration.

## Production impact

None.

Sky Day Trading v1.4 and Sky Swing V1.0 remain the formal production baselines
until the entire promotion funnel is passed.


## Baseline algorithm v1 (frozen before first VNext run)

The first deterministic VNext baseline is fixed as follows before observing any
new VNext output:

1. Horizons: **3D / 5D / 10D only**.
2. Primary target: market-residual forward return only.
3. Industry residual target is disabled until historical point-in-time sector
   mapping is verified.
4. Initial feature set:
   - trend_ma20
   - trend_ma60
   - vol20
   - drawdown20
   - ret20_rank
   - market_breadth20
5. For each horizon, use **Train only** to calculate each feature's Spearman
   Rank IC with the market-residual target.
6. A feature enters baseline v1 only when Train |Rank IC| >= 0.02.
7. Direction is fixed from Train IC sign:
   - positive IC -> higher percentile is better
   - negative IC -> lower percentile is better
8. Daily score = equal-weight mean of the selected direction-adjusted
   cross-sectional percentile ranks. No fitted nonlinear weights.
9. Portfolio selections: **Top3 / Top5 / Top10** each day.
10. Split names:
    - Train = <= 2024
    - Validation = 2025
    - Research Test = 2026
11. 2026 is explicitly **not** fresh untouched OOS.
12. Costs: **0.45% primary** and **0.65% stress** deducted once per selected
    long position's forward return.
13. No threshold, feature direction, feature inclusion, Top-N, or cost setting
    may be changed after seeing Validation or Research Test results in this
    baseline version.
14. Baseline v1 can be archived/rejected after the run; any structural change
    requires a new preregistration version.
