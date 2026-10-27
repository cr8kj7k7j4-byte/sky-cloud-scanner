# W1｜Sky Swing Challenger V1.1 — 2026 Edge Decay Diagnostic

- Date: 2026-10-27
- Scope: diagnostic only
- Production impact: NONE
- Challenger status: HOLD
- Rule changes: NONE
- Threshold retuning: NONE

## 1. Purpose

Diagnose why Sky Swing Challenger V1.1 lost after-cost edge in 2026 without changing any entry, exit, stop, ranking, cost, or portfolio rule.

This report is not a promotion request and must not be used to justify result-driven retuning.

## 2. Evidence base

Canonical daily history artifact:
- GitHub Actions run: 40252311345
- artifact: w3-swing-canonical-daily-history-repaired-40252311345
- symbols loaded in replay: 2,009
- canonical PIT coverage: approximately 96.7%–96.9%
- replay window represented in the artifact: 2023-01 through 2026-10-22
- V1.1 signals: 3,331

Primary diagnostic exit:
- MA20_TRAIL
- round-trip cost: 0.45%

The same frozen V1.1 signal rules were used throughout.

## 3. Headline finding

The 2026 deterioration is primarily a **breakout follow-through / hit-rate failure**, not a collapse in winner magnitude.

### 2023–2025 vs 2026

| Metric | 2023–2025 | 2026 |
|---|---:|---:|
| Signals | 2,937 | 394 |
| 0.45% after-cost expectancy | +0.528% | -1.124% |
| Win rate | 24.82% | 15.48% |
| Stop rate | 86.01% | 93.91% |
| Max-hold survival rate | 13.99% | 6.09% |
| Avg net winner | +10.275% | +9.839% |
| Avg net loser | -2.690% | -3.132% |
| Avg breadth at signal | 0.625 | 0.584 |
| Avg RS percentile | 0.803 | 0.785 |
| Avg initial risk / entry | 2.62% | 2.96% |

Interpretation:
- winner magnitude remained broadly intact;
- the probability of reaching a sustained winner dropped sharply;
- losers became slightly larger;
- initial stops were wider on average;
- signal-date market breadth and relative strength were weaker.

## 4. Early failure diagnostic

Among stopped trades:

| Metric | 2023–2025 | 2026 |
|---|---:|---:|
| Stop on day 1 | 23.67% | 27.57% |
| Stop by day 3 | 48.14% | 54.59% |
| Stop by day 5 | 60.77% | 66.49% |

This supports a regime/continuation hypothesis: 2026 breakouts were more likely to fail shortly after entry rather than develop into sustained trends.

## 5. 2026 monthly behavior

| Month | n | 0.45% expectancy | Win rate |
|---|---:|---:|---:|
| 2026-01 | 87 | -2.058% | 8.05% |
| 2026-02 | 42 | -2.596% | 0.00% |
| 2026-03 | 31 | -2.727% | 9.68% |
| 2026-04 | 43 | +2.299% | 23.26% |
| 2026-05 | 21 | +1.149% | 23.81% |
| 2026-06 | 58 | -1.821% | 20.69% |
| 2026-07 | 28 | -3.059% | 0.00% |
| 2026-08 | 80 | -0.136% | 28.75% |
| 2026-09 | 4 | +2.271% | 25.00% |

The failure is not explained by one isolated month. Negative expectancy appears across multiple independent 2026 periods, with only April/May and a very small September sample positive.

## 6. Breadth diagnostic

2026 underperformance remained negative across essentially all breadth buckets. Most importantly, the historically productive 0.60–0.65 breadth bucket reversed sharply:

| Breadth bucket | 2023–2025 exp. | 2026 exp. |
|---|---:|---:|
| 0.50–0.55 | +0.495% | -0.309% |
| 0.55–0.60 | +1.156% | -0.586% |
| 0.60–0.65 | +0.452% | -2.925% |
| 0.65–0.70 | +0.286% | -0.758% |
| >=0.70 | +0.165% | -2.577% |

This argues against a simple explanation that the frozen breadth >= 0.50 gate alone was too permissive. Retuning that threshold after observing results would also violate preregistration.

## 7. Relative-strength diagnostic

Most RS buckets turned negative in 2026:

| RS percentile | 2023–2025 exp. | 2026 exp. |
|---|---:|---:|
| 0.70–0.75 | +0.106% | -1.422% |
| 0.75–0.80 | +0.644% | -0.298% |
| 0.80–0.85 | +0.746% | -1.933% |
| 0.85–0.90 | +0.307% | -1.278% |
| >=0.90 | +1.274% | +0.874% (n=15 only) |

The >=0.90 subgroup is too small in 2026 to justify a threshold change and must not be used as a rescue rule.

## 8. Initial-risk diagnostic

All major initial-risk buckets were negative in 2026, including buckets that were positive historically. Therefore the observed decay cannot be responsibly attributed to one stop-width bucket.

No stop-width retuning is authorized from this result.

## 9. Structural interpretation

Current evidence supports the following **diagnostic hypothesis**, not a new trading rule:

> In 2026, the V1.1 breakout structure experienced materially weaker post-entry continuation. The strategy still produced occasional large winners, but the conversion rate from breakout signal to sustained trend fell enough that stop frequency and early failure overwhelmed payoff size.

Potential structural causes requiring independent evidence:
1. shorter trend half-life / more frequent false breakouts;
2. faster cross-sectional rotation;
3. increased gap/reversal or mean-reverting behavior after EOD breakout;
4. market/sector leadership concentration not captured by broad market breadth;
5. execution-date context different from signal-date context.

These are research hypotheses only.

## 10. Governance decision

- FIXED_3R: REJECTED for V1.1 evidence.
- MA20_TRAIL: HOLD / diagnostic candidate only.
- SWING10_TRAIL: HOLD / lower priority.
- V1.1 overall: HOLD.
- No Production change.
- No Shadow/Paper promotion from this evidence.
- No local threshold / RS / breadth / stop / holding-period / target retuning.

## 11. Next eligible research

The next experiment, if authorized by W0, should be a **new structural preregistration** aimed at explaining continuation failure rather than optimizing V1.1 thresholds.

Allowed directions include:
- post-breakout continuation label / trend-persistence target;
- PIT sector-leadership persistence;
- cross-sectional rotation / leadership half-life;
- gap-and-reversal context;
- signal-date to execution-date regime transition.

Any successor must have a new strategy/version ID and fresh preregistration before results are observed.
