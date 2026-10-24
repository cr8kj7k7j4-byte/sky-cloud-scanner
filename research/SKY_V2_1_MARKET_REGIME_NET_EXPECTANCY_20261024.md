# Sky V2.1 Market Regime × Net Expectancy

- Date: 2026-10-24
- Status: RESEARCH EVIDENCE ONLY
- Trade ledger: `sky_swing_v18_addon_trade_comparison.csv`
- Market-state table: `sky_swing_v18_market_state_halfyear.csv`
- Trades: 1,161
- Market-state periods: 11 half-year regimes
- Outcome: `base_net_R` (cost-adjusted research outcome from the V1.8 comparison ledger)

## Baseline

Across all 1,161 trades:

- Net Expectancy: **+0.227R**
- PF: **1.678**
- Win rate: **42.5%**

## Candidate market weakness score

One point is assigned for each weak condition:

1. breadth20 < 0.45
2. breadth60 < 0.45
3. ma20up < 0.45
4. medret20 < 0
5. breadth20_20chg < 0

This produces a `weak_score` from 0 to 5.

Important:
- These thresholds are a research surface, not optimized Production parameters.
- The state table contains only 11 half-year observations, so trade count must not be mistaken for 1,161 independent regime observations.

## Result by weakness score

| Weak score | Half-year regimes | Trades | Net Expectancy | PF | Win rate |
|---:|---:|---:|---:|---:|---:|
| 0 | 3 | 377 | **+0.469R** | **2.740** | 49.9% |
| 1 | 1 | 177 | +0.354R | 2.228 | 48.6% |
| 2 | 1 | 128 | +0.027R | 1.080 | 32.8% |
| 3 | 1 | 31 | +0.420R | 2.758 | 54.8% |
| 4 | 1 | 38 | +0.466R | 3.212 | 47.4% |
| 5 | 4 | 410 | **-0.024R** | **0.945** | **34.9%** |

The 3/4-score rows show why this is not a monotonic scoring model yet. The key evidence is the extreme separation between score 0 and score 5.

## Threshold surface

| Rule | Regime periods | Trades | Net Expectancy | PF |
|---|---:|---:|---:|---:|
| weak_score < 1 | 3 | 377 | **+0.469R** | **2.740** |
| weak_score >= 1 | 8 | 784 | +0.111R | 1.303 |
| weak_score < 2 | 4 | 554 | +0.432R | 2.569 |
| weak_score >= 2 | 7 | 607 | +0.040R | 1.104 |
| weak_score < 3 | 5 | 682 | +0.356R | 2.238 |
| weak_score >= 3 | 6 | 479 | +0.044R | 1.109 |
| weak_score < 4 | 6 | 713 | +0.359R | 2.256 |
| weak_score >= 4 | 5 | 448 | +0.018R | 1.043 |
| weak_score < 5 | 7 | 751 | +0.364R | 2.293 |
| weak_score = 5 | 4 | 410 | **-0.024R** | **0.945** |

## Half-year evidence

Examples:

- 2023H1: breadth20 0.609 / breadth60 0.694 / ma20up 0.566 / medret20 +1.25% / weakness score 0  
  → base_net_R Expectancy **+0.507R**, PF **2.898**

- 2025H1: breadth20 0.378 / breadth60 0.396 / ma20up 0.391 / medret20 -2.87% / weakness score 5  
  → base_net_R Expectancy **-0.174R**, PF **0.632**

- 2024H2: weakness score 5  
  → Expectancy +0.130R, PF 1.335

- 2021H2: weakness score 5  
  → Expectancy +0.317R, PF 2.291

This last point matters: score 5 is weak in aggregate, but not every individual half-year is negative. Therefore it is **not yet a Production kill switch**.

## Research interpretation

### Strong evidence
- Market environment materially changes cost-adjusted strategy performance.
- Fully healthy market states (0/5 weak conditions) have substantially higher Net Expectancy and PF than the baseline.
- Fully weak states (5/5 weak conditions) are near or below break-even after costs in aggregate.

### Candidate action
- Keep Market Regime as a mandatory P0-M / P0-R research gate.
- In a fully weak state, prefer:
  - lower Portfolio Heat
  - higher A+ threshold
  - fewer concurrent positions
  - potentially no new long exposure after further validation

### Not promoted
- No automatic Risk-Off kill switch yet.
- No threshold is declared optimal.
- No claim that 0/5 or 5/5 will repeat in future markets.

## ATR-normalized stop-distance status

The ATR-normalized test was **not completed in this pass**.

Reason:
- The accessible Swing ledger does not contain contemporaneous ATR.
- The prior yearly raw OHLC ZIP files were not available as materializable files in the current project/library search.
- Fugle historical-content calls did not return usable OHLC payloads in this session.
- Public full-history CSV retrieval hit environment/tool-size limits.

Per Sky governance, ATR is therefore marked **DATA BLOCKED**, not estimated or imputed.

## Next required data contract

Historical Replay should persist, for every entry:

- ATR14
- ATR percentile
- stop_distance_pct
- stop_distance_ATR = (entry - stop) / ATR14
- market breadth20 / breadth60
- ma20_up_share
- median 20d return
- breadth momentum
- market regime label
- explicit fee / tax / slippage
- execution-adjusted R

## Promotion status

**Market Regime: PASS TO NEXT VALIDATION — NOT PRODUCTION**

**ATR-normalized Stop Distance: DATA BLOCKED — NOT TESTED**
