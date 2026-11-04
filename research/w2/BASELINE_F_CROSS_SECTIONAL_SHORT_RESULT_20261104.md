# W2｜Baseline F Cross-sectional False-Reclaim Short — Final Historical Research Result

- Checked: 2026-11-04 Asia/Taipei
- Hypothesis preregistered: [Baseline F preregistration](../w5/BASELINE_F_CROSS_SECTIONAL_FALSE_RECLAIM_PREREG_20261104.md)
- Code: `research/backtest_baseline_f_cross_sectional_short.py`
- Workflow: [GitHub run 41755026714](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41755026714)
- Evidence artifact: [baseline-f-cross-sectional-result-41755026714](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41755026714/artifacts/13286674377)
- Data provenance: original Baseline E 20 shards from run 40329668748, PIT universe, 2026-01-01 to 2026-10-22
- Workflow result: completed / success; unit tests, input integrity check, report assertions and artifact upload all succeeded.
- Research result: **REJECT_AFTER_COST_EXPECTANCY**
- Production changed: **NO**

## Frozen exploratory test

Causal E short sequence (first strength -> retest -> reclaim -> close below session open -> next-minute entry) retained with unchanged stop/outcomes. New information is exchange-level contemporaneous market median (completed bar close / session open - 1) and the stock's market residual at the breakdown bar. Trade only when both the exchange median and stock residual are below zero. Other-symbol peers only, at least 100 valid contemporaneous peers per event. This is not a retune of Baseline E entry/exit.

Reported short-return conversion uses **(entry-cover)/entry** rather than the earlier E legacy **entry/cover - 1**. Historical E control recomputed on that same corrected basis.

## Actual research evidence

| Metric | Value |
|---|---:|
| Source E selected events | 13,399 |
| E evaluable 60m records (corrected short-return control) | 10,732 |
| F evaluable 60m records | 2,151 |
| F covered trading days | 141 (historical, not forward) |
| F unique stock symbols | 756 |
| F maximum single-symbol concentration | 0.6044% |
| F 60m gross expectancy | +0.249139% |
| F gross PF | 1.6999 |
| F 0.45% net expectancy | **-0.200861%** |
| F 0.45% net PF | **0.7074** |
| F 0.45% net win rate | 24.5467% |
| F 0.65% net expectancy | **-0.400861%** |
| F 0.65% net PF | 0.5227 |
| F opening-price stop-trigger rate | 75.9182% |
| F H1 0.45% expectancy | -0.212361% (n=1,390; PF 0.6956) |
| F H2 0.45% expectancy | -0.179856% (n=761; PF 0.7301) |
| E corrected 0.45% expectancy (same return definition) | -0.244400% (PF 0.6117) |

The historical market-context subset improves descriptive average economics relative to the corrected E control, but **both are materially negative after primary costs**, so F fails its frozen primary gate. Improvement observed within reused 2026 data is not independent confirmation and must not be used to tune additional sign/rank/time parameters.

## Mandatory decision and caveats

**REJECT** as a standalone executable intraday short strategy. No W4 candidate promotion, Paper/Live, or Production change.

The 2026 research sample was already observed by earlier E work, therefore it is **not fresh untouched OOS**. Historical point-in-time short-sale eligibility, stock borrowing availability, adverse short fills/cover risk, capacity and executable bid-ask impact remain **not verified**. Those missing fields would further constrain any executable opportunity, not rehabilitate a negative expectancy.

Frozen completed evidence: the code, pre-registration, immutable GitHub workflow run and artifact. W0/P0-G alone owns formal changes to canonical freeze registry and any Production governance; this W2 note is the completed research record only.
