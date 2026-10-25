# W0 Decision — Top100 Velocity Baseline A

Date: 2026-10-26

## Formal decision

**Top100 Velocity Baseline A: REJECTED_STANDALONE / ARCHIVED_NO_RETUNE**

Production impact: **NONE**.

The user's original concept is separated into two parts:

1. **Top100 current-day gainers as a candidate universe** → retain as FEATURE_ONLY / candidate-pool context.
2. **The frozen Baseline A rule for selecting the fastest names** → reject as standalone alpha.

## Frozen experiment

- Corrected whole-universe PIT 5m source.
- 2,883,178 decision-time input rows.
- 2,007 symbols.
- 831 trading dates.
- 9,934 selected observations.
- Scan times: 09:15 / 09:30 / 09:50 / 10:15.
- Top100 by current-day return.
- Positive 5m price velocity.
- Positive 5m gain-rank velocity.
- Positive 5m volume acceleration.
- Equal-weight percentile score.
- Top3 new symbols per scan.
- Entry proxy: decision-time 5m bar open.
- Exit: 60 minutes later.
- Primary round-trip cost: 0.45%.
- Stress cost: 0.65%.

## Results

### Before costs
- Expectancy: **-0.0388% / observation**
- Win rate: **40.54%**
- PF: **0.953**

### 0.45% cost
- Expectancy: **-0.4888% / observation**
- Win rate: **33.24%**
- PF: **0.556**
- 95% CI for mean: approximately **-0.5312% to -0.4463%**

### 0.65% stress cost
- Expectancy: **-0.6888% / observation**
- Win rate: **29.93%**
- PF: **0.443**

All three chronological folds are negative after cost.
Calendar years 2023, 2024, 2025 and 2026 are all negative after 0.45% cost.

## Interpretation

The frozen rule does not demonstrate standalone continuation alpha.
Its gross PF is already below 1 before transaction costs.

This does **not** prove that the user's discretionary historical process had no edge.
The discretionary process may have contained unrecorded filters such as:
- setup quality;
- location / VWAP;
- anti-chase judgment;
- market / sector context;
- execution judgment.

Those components cannot be retroactively invented after observing this result.

## Governance consequence

- Do not rescue Baseline A by changing Top100 to Top50/Top30.
- Do not search alternate lookbacks.
- Do not optimize Top-N, score weights, exit horizons, stop or target from this sample.
- Re-opening requires a structural new preregistration.

The Top100 universe itself remains a candidate-pool feature only.

## v1.4 comparison status

A fair historical full-stack v1.4 comparison is still unavailable because the authoritative frozen v1.4 historical rule implementation / decision stream was not preserved.
Existing research-only VWAP, Sector RS and Anti-Chase contracts must not be substituted as if they were Production v1.4 rules.

Therefore the honest conclusion is:

**Baseline A failed. Whether v1.4 is better cannot be proven historically from current SSOT.**

Forward Shadow/Paper comparison is the correct route for future Champion–Challenger evidence.
