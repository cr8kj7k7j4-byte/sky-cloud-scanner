# Sky V2.1 Stop-Distance Robustness Surface

- Date: 2026-10-24
- Status: RESEARCH EVIDENCE ONLY
- Dataset: `sky_swing_v17_corrected_continuous.csv`
- Rows: 1,161
- Objective: test whether smaller original stop distance is robust enough to become a hard rule.

## Key result

**Do not convert stop distance into a monotonic "the smaller the better" hard gate.**

The previous ranking ablation showed smaller stop distance was a strong relative-ranking factor. This robustness surface shows that the relationship is not monotonic by absolute stop-distance bucket.

### Stop-distance buckets

| Original stop distance | Trades | PF | Expectancy | MDD | Win rate |
|---|---:|---:|---:|---:|---:|
| <=3% | 114 | 2.696 | +0.490R | -2.78R | 53.5% |
| 3–4% | 101 | 1.826 | +0.285R | -5.51R | 48.5% |
| 4–5% | 155 | 2.600 | +0.433R | -7.19R | 49.7% |
| 5–6% | 157 | 1.931 | +0.292R | -5.27R | 44.6% |
| 6–7% | 176 | 1.684 | +0.187R | -7.30R | 46.0% |
| 7–8% | 146 | 2.586 | +0.415R | -7.06R | 52.1% |
| 8–10% | 197 | 2.535 | +0.382R | -8.01R | 47.7% |
| >10% | 115 | 1.215 | +0.067R | -8.99R | 39.1% |

## Interpretation

1. **The relation is non-monotonic.**
   - 7–10% stop distance still produced strong PF / Expectancy.
   - Therefore, using a universal hard cap such as 5% would discard profitable historical setups.

2. **The clearest weak region is >10%.**
   - PF fell to 1.215.
   - Expectancy fell to +0.067R.
   - Win rate fell to 39.1%.
   - This is materially weaker than the full baseline.

3. **Small stop distance remains useful for ranking, not yet for absolute veto.**
   - Same-day ranking can prefer lower structural risk when multiple candidates are otherwise comparable.
   - The absolute cutoff still needs regime/setup/volatility normalization.

## Absolute cap surface

| Max stop distance | Trades | PF | Expectancy | MDD | 2024+ PF | 2024+ Exp |
|---|---:|---:|---:|---:|---:|---:|
| 3% | 114 | 2.696 | +0.490R | -2.78R | 3.149 | +0.559R |
| 4% | 215 | 2.249 | +0.393R | -5.74R | 2.289 | +0.390R |
| 5% | 370 | 2.383 | +0.410R | -9.71R | 2.289 | +0.355R |
| 6% | 527 | 2.243 | +0.375R | -12.20R | 2.014 | +0.291R |
| 7% | 703 | 2.113 | +0.328R | -15.71R | 1.787 | +0.234R |
| 8% | 849 | 2.187 | +0.343R | -21.02R | 1.859 | +0.254R |
| 9% | 974 | 2.238 | +0.345R | -23.13R | 1.845 | +0.249R |
| 10% | 1,046 | 2.245 | +0.350R | -26.39R | 1.884 | +0.261R |
| 11% | 1,083 | 2.221 | +0.343R | -28.37R | 1.856 | +0.252R |
| 12% | 1,110 | 2.174 | +0.330R | -29.83R | 1.818 | +0.240R |

## Year-by-year warning

A 5% hard cap looked attractive in aggregate, but sample coverage was uneven:
- 2021 had only 1 qualifying trade.
- 2025 improved only slightly versus baseline.
- 2023 was strong, but the pattern is not stable enough to claim 5% is optimal.

A 6–7% cap also failed to improve every year.

## Research conclusion

### Keep
- Use original stop distance as a **P0-O ranking feature**.
- Prefer lower structural risk when otherwise similar candidates compete for limited capital.

### Do not promote
- No universal "stop must be <= X%" Production gate yet.
- Do not tighten stops artificially just to qualify.

### Candidate hypothesis for next validation
- **>10% original stop distance is a high-risk warning zone**, but not yet a Production veto.
- Test normalized stop distance using ATR / volatility / setup class / market regime before defining a hard gate.

## Next validation

1. Normalize stop distance by ATR and volatility.
2. Compare within setup/phase cohorts.
3. Add market regime.
4. Add transaction cost + slippage reconstruction.
5. Walk-forward.
6. Only then decide whether a hard veto exists.

**Promotion status: PASS TO NEXT VALIDATION — NOT PRODUCTION**
