# Sky VNext Residual Ranking Baseline v1 — Decision Record

## Status
**REJECTED / ARCHIVED_NO_RETUNE**

## Date
2026-10-25

## Scope
Pre-registered VNext Residual / Market-Neutral Cross-sectional Ranking Baseline v1.

## Frozen design
- Horizons: 3D / 5D / 10D
- Features: trend_ma20, trend_ma60, vol20, drawdown20, ret20_rank, market_breadth20
- Train-only feature inclusion/direction
- Daily equal-weight direction-adjusted percentile score
- Top3 / Top5 / Top10
- 0.45% primary cost / 0.65% stress
- Train <=2024 / Validation=2025 / Research Test=2026
- 2026 explicitly not fresh untouched OOS

## Label audit
Train selected only:
- vol20: negative direction on 3D / 5D / 10D
- drawdown20: positive direction on 3D / 5D / 10D

vol20 kept the same sign in Validation and Research Test.
drawdown20 weakened materially and flipped sign in 10D Validation.

## Portfolio result
At the 0.45% primary cost, **every preregistered horizon × Top-N variant had negative daily portfolio expectancy in both Validation and Research Test, with PF < 1.0**.

Examples:
- 3D Top10
  - Validation EV -0.443%, PF 0.438
  - Research Test EV -0.366%, PF 0.505
- 5D Top10
  - Validation EV -0.550%, PF 0.463
  - Research Test EV -0.532%, PF 0.480
- 10D Top10
  - Validation EV -0.946%, PF 0.383
  - Research Test EV -0.825%, PF 0.404

0.65% stress cost worsened every variant.

Drawdowns were also unacceptable; many variants suffered portfolio max drawdowns above 60%, with several above 80–90%.

## Governance interpretation
1. The signal-level residual IC did **not** convert into a deployable after-cost portfolio edge.
2. This is the same class of failure previously observed in Weak-Regime research: feature relationship does not imply investable Alpha.
3. Because the preregistered automatic-rejection condition is met, baseline v1 is archived.
4. Do not tune weights, Top-N, horizon, IC threshold, or cost assumptions to rescue this version.
5. Do not escalate this exact feature/label formulation to Random Forest, XGBoost, or LightGBM; doing so after comprehensive negative portfolio evidence would create model-mining risk.
6. No Production impact. Sky Day Trading v1.4 and Sky Swing V1.0 remain unchanged.

## Re-open condition
A future residual-ranking study requires a **new structural preregistration**, not local tuning. At least one of the following must materially change:
- point-in-time data/universe quality,
- target/label construction,
- market horizon,
- execution architecture,
- newly available independent data.

A truly fresh future period is still required before any promotion claim.
