# Sky Research Freeze Registry

> Canonical research governance list. A family marked `ARCHIVED_NO_RETUNE`
> must not be re-opened by another chat, branch, notebook, or researcher merely
> by changing local thresholds. Re-opening requires a documented structural
> change in data, target/label, market horizon, or execution model.

## Frozen / archived families

| Candidate family | Status | Re-open only if |
|---|---|---|
| P0-S 5m Breakout | ARCHIVED_NO_RETUNE | New structural setup family or new untouched data regime; not threshold tweaks |
| Stage 6B Catalyst Score | ARCHIVED_NO_RETUNE | Event evidence used in a materially different horizon/label |
| Stage 6C Event Interaction | ARCHIVED_NO_RETUNE | New pre-registered interaction architecture + untouched data |
| Stage 6D Reaction-first Intraday | ARCHIVED_NO_RETUNE | Different horizon/target or structural execution architecture |
| Stage 7A Broader Market Alpha A1–A5 | ARCHIVED_NO_RETUNE | New point-in-time universe + materially new hypothesis family |
| Weak-Regime Mean-Reversion 5–20D | ARCHIVED_NO_RETUNE | New target engineering, not MA/Top-N/holding-period retuning |
| Fixed-time Intraday Ranking | ARCHIVED_NO_RETUNE | Materially new target or data architecture |
| Event-driven Intraday Ranking / Catalyst Stack | ARCHIVED_NO_RETUNE | Slower horizon or new target family, not intraday threshold tuning |
| Transparent Intraday ML Ensemble | ARCHIVED_NO_RETUNE | New labels / data contract / validation period, not model hyperparameter search |
| Low-vol Market-residual Long-only | ARCHIVED_NO_RETUNE | Cross-sectional residual target / market-neutral formulation |

## Active but blocked research

| Candidate | Status | Blocker |
|---|---|---|
| Revenue MoM 5D | PRE_PIT_CANDIDATE | Historical verified MOPS filing timestamp coverage = 0.0000% |
| Revenue YoY Acceleration 5D | PRE_PIT_CANDIDATE | Historical verified MOPS filing timestamp coverage = 0.0000% |
| Revenue YoY 5D | HOLD_CONCENTRATION_FAIL | Concentration gate failed |
| Revenue YoY 20D | HOLD_CONCENTRATION_FAIL | Concentration gate failed |

## Sole VNext alpha research lane

**Residual / Market-Neutral Cross-sectional Ranking**

This is the only newly authorized Alpha research lane after the current freeze.

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
