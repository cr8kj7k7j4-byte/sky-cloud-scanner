# W2｜Top100 Velocity Baseline A — Final Result 2026-10-26

## Final W2 status

**REJECT**

Production impact: **NONE**  
Sky Day Trading v1.4 remains ACTIVE / unchanged.

This decision applies only to the preregistered **Dynamic Top100 Velocity Baseline A**. It does not reject the Production baseline and does not authorize local parameter rescue.

## Frozen candidate

At 09:15 / 09:30 / 09:50 / 10:15:
- causal current-day Top100 gainers;
- positive price velocity;
- positive gain-rank velocity;
- positive volume-rate acceleration;
- equal-weight percentile score;
- top-decile selection;
- next 5m bar open as deterministic entry;
- fixed 30-minute exit;
- no stop/target optimization.

09:05 is reference-only.

## Canonical historical source

Corrected PIT whole-universe Fugle 5m history:
- workflow run: 40221377923
- retained bars: 54,187,242
- symbols with bars: 2,022
- symbol coverage: 99.8519%
- symbol-day coverage: 98.9071%
- minimum daily coverage: 97.3726%
- historical period: 2023-05-23 through 2026-10-22

2026 is **Research Test**, not fresh untouched OOS.

## Sample

- selected signals: **9,949**
- deterministic entries: **8,685**
- no exact entry bar: **1,264**
- deterministic entry rate: **87.30%**
- unique selected symbols: **1,414**
- maximum single-symbol share: **0.372%**

Entry semantics are fail-closed:
if there is no 5m bar starting exactly at the observation timestamp, the signal is classified **NO_ENTRY_BAR**. No fill or outcome is invented.

## Main result

### Gross / before assumed round-trip cost
- Expectancy: **+0.0215%**
- PF: **1.035**
- Win rate: **40.50%**

Gross edge is therefore only about **2.15 bps per deterministic entry**, far below the preregistered primary transaction-cost assumption.

### Primary cost = 0.45% round trip
- Expectancy: **-0.4285%**
- PF: **0.528**
- Win rate: **31.17%**
- Average win: **+1.540%**
- Average loss: **-1.320%**
- Average MFE: **+1.322%**
- Average MAE: **-1.140%**

### Stress cost = 0.65% round trip
- Expectancy: **-0.6285%**
- PF: **0.402**
- Win rate: **27.27%**

## Split stability — 0.45% cost

| Split | N | Expectancy | PF |
|---|---:|---:|---:|
| Development | 4,361 | -0.3888% | 0.553 |
| Validation 2025 | 2,439 | -0.4996% | 0.461 |
| Research Test 2026 | 1,885 | -0.4281% | 0.560 |

All three periods are negative after cost.

## Half-year stability — 0.45% cost

All **8 / 8** eligible half-year folds have negative expectancy and PF below 1:
- 2023-H1: -0.3271%, PF 0.607
- 2023-H2: -0.3941%, PF 0.522
- 2024-H1: -0.3481%, PF 0.602
- 2024-H2: -0.4389%, PF 0.524
- 2025-H1: -0.5037%, PF 0.453
- 2025-H2: -0.4962%, PF 0.468
- 2026-H1: -0.3476%, PF 0.632
- 2026-H2: -0.5530%, PF 0.456

There is no positive half-year fold to support stability.

## Time-of-day stability — 0.45% cost

| Observation | N | Expectancy | PF |
|---|---:|---:|---:|
| 09:15 | 2,092 | -0.3027% | 0.687 |
| 09:30 | 2,430 | -0.4782% | 0.494 |
| 09:50 | 2,226 | -0.4818% | 0.467 |
| 10:15 | 1,937 | -0.4407% | 0.453 |

All four official trade observation times are negative after cost.

**Do not rescue the candidate by selecting 09:15 after observing the result.**
That would be prohibited result-driven time-of-day retuning.

## Exchange stability — 0.45% cost

- TPEx: N 3,852; Expectancy -0.4125%; PF 0.561
- TWSE: N 4,833; Expectancy -0.4412%; PF 0.501

The result is not explained by one exchange.

## NO_ENTRY sensitivity

The 1,264 NO_ENTRY signals are not assigned hypothetical returns.

Diagnostic only:
to lift all 9,949 selected signals to zero overall expectancy at the 0.45% cost assumption, the NO_ENTRY signals would need to average approximately:
- **+2.944% net return**, or
- **+3.394% gross return**
within the same 30-minute horizon.

Observed deterministic-entry average MFE is only +1.322%.

This sensitivity is not used to fabricate missing fills; it only shows the scale required for missing entries to reverse the observed conclusion.

## W2 interpretation

Observable facts:
- Baseline A has almost no pre-cost edge.
- Primary and stress after-cost expectancy are materially negative.
- Validation and Research Test are both negative.
- All half-year folds are negative.
- All official observation times are negative.
- Both exchanges are negative.
- Concentration is low, so failure is not driven by one symbol.

Analysis inference:
The tested structural hypothesis — Dynamic Top100 + price velocity + rank velocity + volume acceleration with fixed 30-minute holding — **does not provide sufficient after-cost edge** under the preregistered specification.

## Governance decision

**REJECT Baseline A.**

Do not locally rescue this formulation through:
- changing Top100 to another Top-N;
- selecting only 09:15;
- changing velocity lookbacks;
- changing score weights;
- changing the 30-minute horizon;
- adding optimized stop/target values;
- tuning volume thresholds.

Any successor must be a separately preregistered **structural** hypothesis and must pass W5 duplicate / Freeze governance before W2 validation.

Historical full-rule v1.4 comparison remains prohibited by W0 PR #118.

No Production rule changes are authorized by this result.
