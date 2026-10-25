# W1｜Sky Swing Canonical PIT Replay Pre-registration v1.0

> Status: FROZEN RESEARCH CONTRACT  
> Authority: W1 may validate only. W0 remains the only promotion authority.  
> Production baseline remains **Sky Swing V1.0**.

## 1. Research question

Determine whether the existing frozen Sky Swing V1.0 logic, and only already-governed challengers, retain an after-cost edge when replayed on the canonical 2023+ point-in-time TWSE/TPEx universe.

This experiment must not be used to search for a better threshold, holding horizon, feature weight, or exit after seeing results.

## 2. Universe and data

- Market: Taiwan TWSE + TPEx.
- Direction: long only.
- New-entry price rule: < TWD 100 unless the frozen Production rule explicitly states otherwise.
- Historical membership: consume the canonical `pit_intervals.json` emitted by `research/audit_historical_universe.py`.
- Research window: 2023-01-01 onward.
- A symbol is eligible on date D only if the canonical interval contains D.
- Today's listing universe must never be used as a historical substitute.
- Corporate actions, symbol continuity, timestamps and missing data must fail closed when unresolved.

## 3. Time separation

- Train / Validation / OOS must be time ordered.
- At least 3 walk-forward folds.
- Previously inspected 2026 data is NOT fresh OOS.
- No OOS result may be used to change model parameters.
- Truly fresh OOS requires future data that was not used by prior Sky research.

## 4. Cost model

Mandatory:
- Primary round-trip cost: 0.45%.
- Stress round-trip cost: 0.65%.

All reported Expectancy, PF and returns used for governance must be after cost.

## 5. Frozen comparison set

No new result-selected horizon is authorized in this replay.

Existing governed exits to compare:
- FIXED_3R
- MA20_TRAIL
- SWING10_TRAIL
- any additional exit explicitly ACTIVE in the canonical Registry at run time.

Exit selection criterion is stability, not maximum headline return.

## 6. Required Rule Ablation

Remove one at a time, without threshold retuning:
- Market Gate
- Trend
- Relative Strength
- Anti-Chase
- Setup
- Trigger
- RR Gate
- Exit Rule

Record whether each component:
1. improves after-cost Expectancy;
2. reduces Max Drawdown;
3. is stable across >=3 folds;
4. is stable across Bull / Neutral / Bear;
5. merely changes trade count.

## 7. Required Feature Ablation

For every feature used by the frozen candidate:
- Full model baseline.
- Single-feature remove-one.
- Group ablation where applicable.
- Report Expectancy / PF / Max DD / sample count by fold and regime.
- No feature is kept or removed from Production directly from this lab.

## 8. Portfolio validation

Mandatory:
- Max concurrent positions.
- Fixed-risk / 1R sizing.
- Correlation exposure.
- Sector concentration.
- Single-symbol concentration.
- Portfolio Heat.
- Capacity / liquidity.
- Turnover.
- Max Drawdown.
- Kill-switch interaction.

A signal-level positive result does not pass without portfolio-level evidence.

## 9. Mandatory metrics

At minimum:
- Sample Count
- Win Rate
- Avg Win
- Avg Loss
- Expectancy
- Profit Factor
- Max Drawdown
- MAE
- MFE
- R Multiple
- Turnover
- Cost-adjusted return
- Bull / Neutral / Bear
- Annual stability
- Fold stability

## 10. Promotion gate

W1 final status may only be:
- PROMOTE_CANDIDATE
- HOLD
- REJECT
- ARCHIVE

PROMOTE_CANDIDATE requires all non-future gates to pass, including PIT, leakage/survivorship, walk-forward, 0.45% and 0.65% cost stress, regime stability, portfolio/capacity and concentration.

Even then, the candidate may only be sent to W4 Shadow/Paper. W1 cannot change Production.

## 11. Fail-closed blockers

Return `BLOCKED` rather than infer or impute when:
- canonical PIT intervals are absent or invalid;
- price-history coverage is materially incomplete;
- corporate-action or symbol-continuity evidence is missing where material;
- sector mapping is required but not point-in-time;
- a required exit/rule cannot be reproduced exactly.

Return `WAITING_FOR_FUTURE_DATA` for fresh OOS and prospective Shadow/Paper evidence.
