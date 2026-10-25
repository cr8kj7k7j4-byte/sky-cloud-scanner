# P0-S 5m Breakout — Decision Record

## Status
**REJECTED / ARCHIVED_NO_RETUNE**

## Date
2026-10-25

## Scope
Sky P0-S deterministic 5-minute breakout candidate.

Frozen design:
- Lookback: previous 4 x 5-minute bars
- Trigger: highest high of prior 4 bars
- Stop: lowest low of prior 4 bars
- Target: 2.0R
- Max acceptable entry: Trigger + 0.25R
- Risk bounds: 0.30%–2.50%
- Max hold: 24 x 5-minute bars
- Average/VWAP guard retained
- Same-bar stop/target ambiguity: conservative stop-first
- Primary round-trip cost stress: 0.45%

## Data / OOS contract
- Historical period: 2023-05-23 to 2026-10-24
- OOS starts: 2026-01-01
- Deterministic sample: 100 stocks
  - TWSE 50
  - TPEx 50
- Historical 5m bars validated: 2,704,785
- Successful symbol downloads: 100 / 100
- Missing/empty/parse-error files: 0

## OOS result
Primary 0.45% cost:
- n = 9,111
- win rate = 22.15%
- Expectancy = -0.8018R
- PF = 0.2033
- Avg win = +0.9236R
- Avg loss = -1.2927R
- Avg MFE = +0.6817R
- Avg MAE = -0.7489R
- Verdict = RESEARCH_ONLY

## Cost sensitivity
The failure is not explained by trading cost alone.

At 0.00% cost:
- Expectancy = -0.1759R
- PF = 0.6696

At 0.20% cost:
- Expectancy = -0.4541R
- PF = 0.3831

At 0.45% cost:
- Expectancy = -0.8018R
- PF = 0.2033

Therefore the naked breakout candidate has negative expectancy before realistic costs.

## Excursion evidence
- MFE >= 0.5R: 43.73%
- MFE >= 1.0R: 27.29%
- MFE >= 1.5R: 16.78%
- MFE >= 2.0R: 10.11%
- MAE <= -0.5R: 70.93%
- MAE <= -1.0R: 47.22%

The 2R target is reached by only a small minority of trades, while adverse excursion is frequent.

## Breakdown

### By risk%
No risk bucket has positive expectancy.

Best observed bucket:
- Risk 2.01%–2.50%
- n = 540
- Expectancy = -0.2435R
- PF = 0.5187
- Win rate = 30.0%

### By entry time
No time bucket has positive expectancy.

Best observed time bucket:
- 09:00–09:29
- n = 1,524
- Expectancy = -0.5640R
- PF = 0.3252
- Win rate = 27.62%

### By exit
- STOP: n = 4,292, Expectancy = -1.7021R
- STOP_AMBIGUOUS: n = 10, Expectancy = -2.1920R
- TARGET: n = 1,171, Expectancy = +1.2802R
- TIME: n = 3,638, Expectancy = -0.4060R

The strategy is dominated by stop losses and negative time exits.

## Governance interpretation
1. The candidate fails OOS by a wide margin.
2. The failure persists even with zero transaction cost.
3. No tested time bucket or risk bucket produces positive expectancy.
4. This is not a parameter-tuning problem; the naked setup family lacks sufficient edge.
5. Do not rescue this family by changing:
   - target R,
   - max-entry R,
   - stop width,
   - time window,
   - risk bucket,
   - cost assumption,
   - lookback bars,
   solely based on these observed results.
6. Do not escalate this exact naked-breakout formulation to ML after seeing the negative OOS result.
7. No Production impact. Existing Sky Production decisions remain governed by Market / Sector RS / Phase / Anti-Chase / Risk / Execution gates.

## Re-open condition
Re-opening requires a new structural preregistration with materially different information content, not local retuning.

Acceptable structural changes include:
- adding independent point-in-time Market regime evidence,
- adding Sector Relative Strength evidence,
- adding Phase / Anti-Chase structure,
- materially different target/label or execution architecture,
- a new untouched future OOS period.

Any successor must follow:
Hypothesis → Pre-registration → Validation → OOS → Cost Stress → Walk-forward → Paper/Shadow → P0-G review.

## Final decision
**P0-S 5m Breakout (naked setup) is rejected and archived.**
