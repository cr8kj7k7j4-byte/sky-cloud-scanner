# W1｜Trend Persistence V1.0 Exploratory Replay — 2026-10-27

- Status: EXPLORATORY_ONLY
- Production impact: NONE
- Promotion eligibility: NO
- Reason: deterministic score formula was not fully committed to GitHub before the first replay result was observed.

## Data
- Canonical repaired Swing daily artifact: GitHub Actions run 40252311345
- Symbols loaded: 1,972
- Breakout-event signals: 3,465
- Top-decile score observations: 525
- Window: 2023-01-01 through 2026-10-22

## Frozen breakout-event baseline
The event sample used the V1.1 breakout definition:
- breadth >= 0.50
- close > MA20 > MA60
- 20D RS percentile >= 0.70
- close > prior 20D high
- distance from MA20 <= 8%
- daily range / close <= 8%
- next-open price < TWD 100

## Exploratory persistence score
The exploratory score used equal weights across 11 D-close features, each converted to same-date cross-sectional percentile:
positive direction:
- breadth
- 5D breadth change
- 20D RS percentile
- 5D RS change
- volume / 20D average volume
- prior 5D return
- prior 20D return

inverse direction:
- distance from MA20
- signal-day range %
- 20D realized volatility
- gap %

The top decile was selected by same-date score percentile >= 0.90.

## Results

### All breakout events
| Cost | n | Expectancy | PF |
|---|---:|---:|---:|
| 0.45% | 3,465 | -0.2643% | 0.8624 |
| 0.65% | 3,465 | -0.4643% | 0.7729 |

### Exploratory score top decile
| Cost | n | Expectancy | PF |
|---|---:|---:|---:|
| 0.45% | 525 | +0.3184% | 1.1886 |
| 0.65% | 525 | +0.1184% | 1.0655 |

### Historical split — top decile
| Split | 0.45% Exp. | 0.65% Exp. |
|---|---:|---:|
| Train | +0.0949% | -0.1051% |
| Validation | +0.0636% | -0.1364% |
| Research Test | +0.9122% | +0.7122% |

### Walk-forward test windows — top decile
| Fold | 0.45% Exp. | 0.65% Exp. |
|---|---:|---:|
| Fold 1 | +0.2600% | +0.0600% |
| Fold 2 | +0.3075% | +0.1075% |
| Fold 3 | +0.7381% | +0.5381% |

### Yearly — top decile
| Year | 0.45% Exp. | 0.65% Exp. |
|---|---:|---:|
| 2023 | -0.0364% | -0.2364% |
| 2024 | +0.2349% | +0.0349% |
| 2025 | +2.1154% | +1.9154% |
| 2026 | -0.6438% | -0.8438% |

## Concentration
- Single-symbol share: 1.14%
- Top-5-symbol share: 5.33%

## Interpretation
The exploratory ranking contains potentially useful independent information because the unranked breakout population is negative after cost while the top decile becomes positive in aggregate and in all three historical walk-forward test windows.

However, this is not promotion-grade evidence:
1. the exact deterministic score formula was not externally frozen before first replay;
2. 2026 remains negative;
3. the 0.65% Validation split is negative;
4. the required Bull/Neutral/Bear regime gate is DATA_BLOCKED because the canonical daily artifact used here does not include a PIT-safe market benchmark series;
5. 2026 has already been inspected and cannot be called fresh OOS.

## Governance decision
- V1.0 exploratory replay: HOLD / EXPLORATORY_ONLY
- Production: unchanged
- No Shadow/Paper promotion
- No threshold/weight rescue
- Any formal successor must use an exact preregistered score and future fresh OOS only.
