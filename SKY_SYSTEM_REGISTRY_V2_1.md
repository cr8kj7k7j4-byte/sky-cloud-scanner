# Sky System Registry V2.1

> Canonical registry for production, research, rejected and evidence-only components.
> Engineering maturity labels do not imply profitability or future returns.

## Canonical architecture
P0-DATA → P0-K → P0-M → P0-EVT → P0-F → P0-AG → P0-S → P0-C → P0-O → P0-R → P0-X → P0-A → PMS → P0-L → P0-D → P0-G

Research namespaces:
- P0-ML: ML Research & Model Arena
- P0-LAB: Candidate Strategy Lab
- P0-PER: Personal Intelligence

## Production baselines

| Type | System / Model | Status | Notes |
|---|---|---|---|
| Production | Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP | ACTIVE | Current formal intraday baseline. No automatic promotion from research. |
| Production | Sky Swing V1.0 | ACTIVE | Current formal 3–20D long-only swing baseline. |

## Active research candidates

| Candidate | Status | Priority | Current evidence |
|---|---|---:|---|
| Swing 5D 3-factor top-decile challenger | HOLD | 3 | Existing 100-symbol artifact is current-universe backward and fails artifact-level PIT/survivorship promotion gate; 0.65% stress-cost stability is inconsistent; portfolio/risk and Shadow/Paper gates incomplete. Do not result-select longer horizons from observed data. |
| Revenue MoM 5D | PRE_PIT_CANDIDATE | 1 | Robustness gates passed, but 2023–2026 historical PIT audit found 0 / 87,588 company-months with verified MOPS filing timestamps (0.0000%). Promotion blocked until historical PIT coverage is resolved or the research window is redefined prospectively. |
| Revenue YoY 5D | HOLD_CONCENTRATION_FAIL | 4 | Primary/stress return gates passed, but top-5-symbol concentration exceeded threshold across splits. Do not promote. |
| Revenue YoY Acceleration 5D | PRE_PIT_CANDIDATE | 2 | Robustness gates passed, but 2023–2026 historical PIT coverage is 0.0000% (0 / 87,588 company-months). Remains pre-promotion research only; statutory-deadline proxies do not satisfy PIT. |
| Revenue YoY 20D | HOLD_CONCENTRATION_FAIL | 5 | Return gates passed, but concentration gate failed; do not promote despite high average returns. |

## Evidence-only features

| Evidence | Status | Use |
|---|---|---|
| vol20 market-residual relationship | FEATURE_ONLY | P0-F contextual feature; not a standalone long-only trigger. |
| drawdown20 residual evidence | FEATURE_ONLY | Research evidence only. |
| market breadth / relative strength | FEATURE_ONLY / CONTEXT | Market and ranking context; not standalone production alpha. |
| Top100 gainers universe | FEATURE_ONLY / CANDIDATE_POOL | Candidate-universe context only. Two independently preregistered Top100 Velocity selector variants failed after cost; Top100 membership alone is not a trade signal. |ndidate-universe context only. Frozen Baseline A velocity selector was rejected; Top100 membership alone is not a trade signal. |

## Rejected candidate families

| Candidate family | Status | Reason |
|---|---|---|
| P0-S 5m Breakout Candidate | REJECTED_OOS | Full 100-symbol validation passed; OOS n=9,111, PF=0.2033, Expectancy=-0.8018R at 0.45% round-trip cost. Do not promote to Paper Trading or live signal. |
| Weak-Regime Mean-Reversion 15D | REJECTED | Signal-level edge failed to survive ranking/capacity/broad-basket portfolio implementation. |
| Fixed-time intraday ranking | REJECTED | OOS and post-cost evidence insufficient. |
| Event-driven intraday ranking / catalyst stack | REJECTED | OOS and post-cost evidence insufficient. |
| Transparent intraday ML feature ensemble | REJECTED | Negative post-cost Train/Valid/Test performance. |
| Low-vol market-residual long-only | REJECTED_AS_STRATEGY | Stable IC did not convert into robust tradable long-only edge. |
| Stage 7A Broader Market Alpha | REJECTED | Pre-registered A1–A5 hypotheses failed stable-positive and cost gates; archived and no further local retuning allowed. |
| VNext Residual Ranking Baseline v1 | REJECTED | All preregistered 3D/5D/10D × Top3/5/10 variants had negative Validation and Research-Test expectancy after 0.45% cost with PF < 1; do not retune or escalate to nonlinear ML. |
| Top100 Velocity Baseline A family | REJECTED_STANDALONE / ARCHIVED_NO_RETUNE | Dual negative evidence: A1 Top3/60m n=9,934, 0.45% expectancy -0.4888%, PF 0.556; A2 top-decile/30m 9,949 signals / 8,685 entries, 0.45% expectancy -0.4285%, PF 0.528, 8/8 half-year folds negative. No local Top-N/time/lookback/weight/holding/stop-target rescue. Top100 universe remains FEATURE_ONLY context. |n=9,934; gross expectancy -0.0388%, gross PF 0.953; 0.45% expectancy -0.4888%, PF 0.556; all folds and 2023-2026 slices negative. Top100 universe retained as FEATURE_ONLY candidate-pool context. |

| Opening Retest Reclaim Baseline D | REJECTED_STANDALONE / ARCHIVED_NO_RETUNE | 2026-01-01–2026-10-22 whole-market 1m PIT; n=12,967; gross 60m expectancy +0.1032%, PF 1.312; 0.45% expectancy -0.3468%, PF 0.506; 0.65% expectancy -0.5468%, PF 0.372; open-stop rate 85.08%; H1/H2 both negative after cost. |

## Historical Universe / Survivorship audit

- Main-native live audit run: GitHub Actions #40177304792 (2026-10-25)
- Governed research window: 2023-01-01 onward
- Official sources healthy: 6 / 6
- Official events: 2,426
- Windowed intervals: 2,116
- Window unresolved events: 0
- Interval validation: PASS
- Historical source coverage: PASS
- Current interval coverage: TPEx 100.0000%; TWSE 99.9081%
- PIT membership: 2023-12-31 = 1,904; 2024-12-31 = 1,960; 2025-12-31 = 2,028; 2026-09-30 = 2,069
- Historical Universe Gate: **PASS for the governed 2023+ research window**
- Promotion-grade 2023+ research must use the point-in-time universe rather than today's listing universe.
- Full-history strict ledger still contains 231 pre-window unresolved events; do not describe this as complete all-history coverage.

## Historical Revenue PIT coverage audit

- Audit run: GitHub Actions #40168078271 (2026-10-25)
- Scope: TWSE + TPEx monthly revenue, 2023-01 through 2026-09
- Expected company-months: 87,588
- Verified MOPS filing timestamps: 0
- Historical PIT coverage: 0.0000%
- Gate: FAIL
- Governance consequence: Revenue candidates remain PRE_PIT_CANDIDATE.
- The MOPS latest-finance endpoint `t51sb10` supports latest records only; its more-info form exposed only `Stp` and `TK`, with no year/month/date history selector in the probed official interface.

## Promotion gate

A Research Candidate may become Production only after ALL of the following 18 gates pass:
1. Point-in-Time Data Alignment.
2. Leakage Check.
3. Survivorship Bias Check.
4. Pre-registration.
5. Train / Validation Separation.
6. OOS.
7. Walk-forward.
8. Market Regime Stability.
9. 0.45% primary round-trip cost test.
10. 0.65% stress round-trip cost test.
11. Portfolio Validation.
12. Concentration Validation.
13. Correlation Validation.
14. Capacity / Liquidity Validation.
15. Max Drawdown.
16. Shadow / Paper Trading.
17. P0-R Risk Gate.
18. P0-G Promotion Review.

Any material gate failure blocks Promotion. No chat window, notebook, branch, or researcher may override this by subjective confidence or local retuning.

## W0 governance authority

- W0｜Sky 總控與版本治理 is the only control workstream authorized to consolidate W1–W7 outcomes into formal Strategy Registry / Research Freeze / Champion-Challenger decisions.
- GitHub remains the Single Source of Truth; a chat-only conclusion is not a formal version change.
- W1/W2 may validate and report candidates but may not self-promote Production.
- Major governance changes must be written back to GitHub.
- W0 does not absorb bulk repetitive backtesting; that remains delegated to W1 / W2.

## Hard governance rules
- Research cannot bypass P0-C or P0-R.
- News and event evidence are not direct trade signals.
- No single Agent can create an executable trade.
- Missing evidence is UNKNOWN / VERIFY_BEFORE_TRADE.
- TRIGGERED does not mean automatic buy.
- Formal production baselines remain unchanged until promotion gates pass.

## Validation evidence state

- W1 Swing validation: **HOLD**; no promotion-grade Swing challenger is currently authorized.
- W4 Shadow/Paper: **WAITING_FOR_SUFFICIENCY**; minimum gate remains >=200 evaluable samples, >=20 trading days, >=2 regimes, >=95% outcome completeness, <=20% single-symbol share, plus portfolio/cost/capacity, P0-R and P0-G review.
- W5 Candidate Lab: no active VNext Alpha candidate is currently authorized.
- Production baseline remains unchanged until all 18 Promotion Gates pass.

## W2 intraday validation infrastructure — updated 2026-10-26

- PR #79 research infrastructure remains accepted by W0/P0-G.
- Accepted components: canonical Intraday PIT Replay Contract, fail-closed validator, 10-Rule ablation, walk-forward/regime stability, 0.45%/0.65% cost stress, W2 validation runner, CI tests.
- Sky Day Trading v1.4 / P0-C MVP remains the Production baseline and its behavior is unchanged.
- No Day Trading rule is newly promoted to Production Stable Rule.
- Corrected whole-universe 5m PIT market source now **PASS**.
- W0 governance decision: historical full-rule replay for Production v1.4 is **NOT FULLY RECONSTRUCTABLE from the current SSOT**.
- Formal W2 status: **HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**.
- W2 must not report historical 10-rule efficacy for v1.4 from reconstructed/proxy rules.
- W2 remains available for future challengers and any strategy whose frozen implementation + PIT evidence are complete.
- Canonical decision: `docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md`.

## Workstream operating state — 2026-10-25

- W0: Master Control / P0-G — ACTIVE.
- W1: Swing Validation — HOLD.
- W2: Intraday Validation — **HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**; future challenger validation remains available.
- W3A: Data & Feature Engineering — canonical PIT / whole-universe market data source ready; maintain data provenance and do not synthesize missing v1.4 Alpha rules.
- W3B: Cloud & Production Engineering — ACTIVE / P1, supporting reproducible forward evidence pipeline and Production hardening.
- W4: Shadow/Paper/Live Evidence — **P0 HIGHEST PRIORITY / WAITING_FOR_SUFFICIENCY**; active forward evidence accumulation.
- W5: Candidate Strategy Lab — INTAKE ONLY.
- W6: Execution & Market Microstructure Lab — ACTIVE / P2, execution evidence only.
- W7: Global Trading Intelligence & Vendor Lab — ACTIVE / P4, low-intensity intelligence/vendor research.
- Legacy W3: DEPRECATED FOR NEW WORK.

Current critical path: **W4 → P0-R / W6 execution evidence → W0 / P0-G**.

## W3A historical intraday coverage status — updated 2026-10-26

- W3A replay engineering framework: **ENGINEERING COMPLETE**.
- Corrected whole-universe 5m PIT raw source: **PASS**.
- Source run: GitHub Actions #40221377923.
- Symbols with bars: 2,022 / 2,025 expected = **99.8519% symbol coverage**.
- Symbol-day coverage: **98.9071%**.
- Minimum daily coverage: **97.3726%**.
- Bars kept after corrected PIT membership filtering: **54,187,242**.
- Duplicate bars: 0; conflicting duplicates: 0; out-of-membership bars: 0.
- The old ~100-symbol artifact remains engineering-only historical evidence, but it is no longer the best available intraday source.
- Current v1.4 historical blocker is **missing authoritative frozen v1.4 rule provenance**, not market-data breadth.
- New preregistered challengers with frozen executable rules, including Top100 Velocity, may use the corrected whole-universe source for historical validation.

## W5 / W7 inbound queue — 2026-10-25

- PR #93 merged: `efae134bda8318bb018a251e0c679726e0af3e44`.
- ACCEPT_FOR_PREREGISTRATION: **0**.
- HOLD: **3**.
- Priority 1: Overnight-to-First-30m Reversal — HOLD / DATA_BLOCKED.
- Priority 2: Dynamic Futures/ETF/Spot Lead-Lag — HOLD / DATA_BLOCKED pending synchronized timestamp/session/roll causality.
- Priority 3: Broker-Identity / Skill-Conditioned Flow — HOLD / HARD DATA GATE / DO_NOT_BUY NOW.
- No Production change and no new formal Pre-registration authorization.

## Intraday PIT data acquisition policy — 2026-10-26

- Current bottleneck: promotion-grade whole-universe synchronized historical intraday coverage, not framework implementation.
- Acquisition sequence is fixed:
  1. Existing Fugle historical-minute capability / GitHub secret feasibility probe.
  2. If and only if that cannot reach the governed PIT gate, evaluate minimum official paid TWSE + TPEx historical intraday products.
  3. Paid purchase requires explicit user approval and does not itself satisfy validation gates.
- TWSE order-type history and Broker Flow data are not authorized purchases at this stage.
- W2, Overnight Reversal and Dynamic Lead-Lag remain HOLD while Gate 0 is unresolved.


## Realtime command routing — 2026-10-27

Canonical contract: `docs/SKY_REALTIME_COMMAND_CONTRACT_V1_0.md`.

- Current/update/scan/position/alert/full-analysis Sky commands are realtime-first.
- Whole-market scans use TWSE + TPEx official current universe plus TWSE MIS TSE + OTC operational quotes.
- Single-stock and position updates require the latest obtainable quote and timestamp before decision output.
- Unrecognized current-state Sky commands fail closed as `REALTIME_REQUIRED_UNROUTED`; they must not silently use stale web rankings.
- Historical backtest and validation commands remain PIT historical workflows.
- Realtime data connectivity does not change strategy promotion state, Alpha rules, stops, targets, or P0-R/P0-G governance.
