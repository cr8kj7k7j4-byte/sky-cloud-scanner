# Sky Research Freeze Registry

> Canonical research governance list. A family marked `ARCHIVED_NO_RETUNE`
> must not be re-opened by another chat, branch, notebook, or researcher merely
> by changing local thresholds. Re-opening requires a documented structural
> change in data, target/label, market horizon, or execution model.

## Frozen / archived families

| Candidate family | Status | Re-open only if |
|---|---|---|
| P0-S 5m Breakout | ARCHIVED_NO_RETUNE | OOS n=9,111, PF 0.2033, Expectancy -0.8018R at 0.45% cost; re-open only via structural preregistration, not threshold tweaks |
| Stage 6B Catalyst Score | ARCHIVED_NO_RETUNE | Event evidence used in a materially different horizon/label |
| Stage 6C Event Interaction | ARCHIVED_NO_RETUNE | New pre-registered interaction architecture + untouched data |
| Stage 6D Reaction-first Intraday | ARCHIVED_NO_RETUNE | Different horizon/target or structural execution architecture |
| Stage 7A Broader Market Alpha A1–A5 | ARCHIVED_NO_RETUNE | New point-in-time universe + materially new hypothesis family |
| Weak-Regime Mean-Reversion 5–20D | ARCHIVED_NO_RETUNE | New target engineering, not MA/Top-N/holding-period retuning |
| Fixed-time Intraday Ranking | ARCHIVED_NO_RETUNE | Materially new target or data architecture |
| Event-driven Intraday Ranking / Catalyst Stack | ARCHIVED_NO_RETUNE | Slower horizon or new target family, not intraday threshold tuning |
| Transparent Intraday ML Ensemble | ARCHIVED_NO_RETUNE | New labels / data contract / validation period, not model hyperparameter search |
| Low-vol Market-residual Long-only | ARCHIVED_NO_RETUNE | Cross-sectional residual target / market-neutral formulation |
| VNext Residual Ranking Baseline v1 | ARCHIVED_NO_RETUNE | New structural preregistration only; no weight/Top-N/horizon/ML rescue of v1 |
| Top100 Velocity Baseline A family | ARCHIVED_NO_RETUNE | Two preregistered variants both failed after cost: (A1) Top3 / 60m, n=9,934, gross PF=0.953, 0.45% expectancy=-0.4888%, PF=0.556; (A2) top-decile / 30m, 9,949 signals / 8,685 deterministic entries, gross expectancy=+0.0215%, PF=1.035, 0.45% expectancy=-0.4285%, PF=0.528, 8/8 half-year folds negative. Re-open only via structural new information/label/execution preregistration, not Top-N/time/lookback/weights/volume threshold/holding-period/stop-target retuning. |n=9,934; gross PF=0.953; 0.45% expectancy=-0.4888%; PF=0.556; all 3 folds and 2023-2026 yearly slices negative after cost. Re-open only via structural new preregistration, not Top-N/lookback/weight/exit retuning. |

## Active but blocked research

| Candidate | Status | Blocker |
|---|---|---|
| Revenue MoM 5D | PRE_PIT_CANDIDATE | Historical verified MOPS filing timestamp coverage = 0.0000% |
| Revenue YoY Acceleration 5D | PRE_PIT_CANDIDATE | Historical verified MOPS filing timestamp coverage = 0.0000% |
| Revenue YoY 5D | HOLD_CONCENTRATION_FAIL | Concentration gate failed |
| Revenue YoY 20D | HOLD_CONCENTRATION_FAIL | Concentration gate failed |

## VNext alpha research status

**No active VNext Alpha candidate is currently authorized.**

Residual / Market-Neutral Cross-sectional Ranking Baseline v1 has been rejected.
Any successor requires a new structural preregistration; the current v1 may not be rescued by local retuning or nonlinear model escalation.

- Labels: 3D / 5D / 10D residual return.
- Residual return = stock forward return minus market benchmark return, with
  industry/sector residualization added only when point-in-time sector mapping
  is available and verified.
- Selection method: daily cross-sectional ranking.
- First baselines: deterministic rule/rank baseline, linear baseline.
- Model challengers after baselines: Random Forest, XGBoost, LightGBM.
- LSTM / Transformer / reinforcement learning are out of scope.
- 2026 data already used in prior research must not be described as fresh
  untouched OOS. A new future period is required for truly fresh OOS.

## Mandatory research funnel

`Hypothesis → Pre-registration → Train → Validation → OOS → Walk-forward → Cost Stress → Capacity/Concentration → Shadow/Paper → P0-G Promotion Review`

Rules:
1. No result-driven threshold changes after pre-registration.
2. No candidate may skip portfolio/capacity validation.
3. No Accuracy-only promotion.
4. No single positive year/subgroup can justify promotion.
5. A rejected family is negative evidence and must stay archived.
6. Promotion requires after-cost positive expectancy and acceptable drawdown,
   not merely a high win rate.

| Top100 Open-Price Gate Baseline B | ARCHIVED_NO_RETUNE | n=1,244; 0.45% expectancy=-0.5190%; PF=0.393; all folds and 2023-2026 slices negative. Open-price gate did not improve Baseline A. |
