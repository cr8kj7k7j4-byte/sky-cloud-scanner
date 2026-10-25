# Sky Master Control Status — 2026-10-25

> 這是目前 Sky 的總控狀態板。正式策略狀態仍以 /SKY_SYSTEM_REGISTRY_V2_1.md 與 /research/RESEARCH_FREEZE_REGISTRY.md 為準。

## A. Production
- Day Trading v1.4 / P0-C MVP — ACTIVE
- Swing V1.0 — ACTIVE
- Baseline — FROZEN at Sky V2.1

## B. Completed Governance
- Canonical architecture — DONE
- Strategy/System Registry — DONE
- Research Freeze Registry — DONE
- 2023+ PIT Universe Gate — PASS
- Validation funnel — DEFINED
- Multi-window operating model — DEFINED
- Shadow/Paper outcome contract — DEFINED

## C. Rejected / Archived
- P0-S 5m Breakout — REJECTED_OOS
- Fixed-time Intraday Ranking — REJECTED
- Event-driven Intraday Ranking / Catalyst Stack — REJECTED
- Transparent Intraday ML — REJECTED
- Weak-Regime Mean-Reversion — REJECTED
- Low-vol Market-residual Long-only — REJECTED_AS_STRATEGY
- Stage 7A Broader Market Alpha — REJECTED
- VNext Residual Ranking Baseline v1 — REJECTED

Action: 不再局部調參重開。

## D. Active / Blocked Research
1. Revenue MoM 5D — PRE_PIT_CANDIDATE — Blocked by historical filing timestamp coverage.
2. Revenue YoY Acceleration 5D — PRE_PIT_CANDIDATE — Same blocker.
3. Revenue YoY 5D — HOLD_CONCENTRATION_FAIL.
4. Revenue YoY 20D — HOLD_CONCENTRATION_FAIL.

## E. Highest-Priority Remaining Gates

### P1 — Swing Evidence Completion
- Consolidate existing Swing robustness/stability evidence.
- Confirm Walk-forward/OOS/cost/regime/portfolio gates against current canonical PIT universe.
- If all pass, queue for Shadow/Paper only; no direct live promotion.

### P2 — Shadow/Paper Evidence Accumulation
Sufficiency candidate gate:
- >=200 evaluable samples
- >=20 trading days
- >=2 regimes
- >=95% outcome completeness
- <=20% single-symbol share

### P3 — Intraday Research Discipline
- Do not reopen rejected intraday families by threshold tuning.
- Any new intraday candidate must have structural preregistration and distinct hypothesis/data/label/execution architecture.

### P4 — Data / Production Engineering
- Strict TPEx official intraday all-market chain
- Feature schema/versioning/DQ productionization
- Alert retry/dedup
- Mobile/Dashboard API
- Champion promotion/rollback rehearsal

## F. Current Strategic Decision

STOP adding broad new modules.

Priority order:
1. Evidence completion
2. Shadow/Paper accumulation
3. Portfolio/risk validation
4. Production hardening
5. Only then new alpha research

## G. Promotion Rule

No candidate becomes Production unless:
PIT + leakage/survivorship + preregistration + walk-forward + OOS + cost stress + portfolio/capacity + shadow/paper + P0-R + P0-G all pass.

## H. Definition of "Stable Profitability"

不定義為每日獲利或保證獲利。
定義為：
- after-cost positive expectancy across adequate samples;
- acceptable and controlled drawdown;
- robustness across time and regimes;
- implementation/live performance close enough to research expectation;
- automatic risk reduction when edge deteriorates.

## I. Next Human Decision Needed

目前沒有。既有授權範圍內可繼續依 Workstream 執行。
真正需要使用者介入的情況僅限：
- 需要新的外部帳號／憑證；
- 不可逆部署或資金風險；
- 需使用者指定可承受 1R／實盤資金；
- 研究資料來源本身無法取得。

## J. W0 Convergence Update — 2026-10-25

### W1｜Swing Validation
- Formal status: **HOLD**.
- Existing 100-symbol Swing artifact is not promotion-grade because it uses the current universe backward and therefore fails the artifact-level PIT / survivorship gate.
- 5D challenger shows mixed walk-forward stability and fails consistent 0.65% stress-cost stability.
- Portfolio overlap, correlation/sector concentration, capacity/liquidity, complete ablation and Shadow/Paper gates remain incomplete.
- Governance action: **do not rerun the same current-universe artifact as if it were new evidence**. The next eligible W1 experiment must be pre-registered and consume the canonical 2023+ PIT universe.

### W2｜Intraday Validation
- No rejected intraday family may be reopened by local threshold, Top-N, indicator-period, weight, stop or target retuning.
- No active intraday Challenger is authorized for Production review.

### W3｜Data / Production Engineering
- Priority remains PIT/data contracts, Feature schema/DQ, TPEx official chain, alert retry/dedup, runtime/E2E and rollback readiness.
- Engineering acceptance is not profitability evidence.

### W4｜Shadow / Paper / Live Evidence
- Formal status: **WAITING_FOR_SUFFICIENCY**.
- Promotion candidate minimum remains >=200 evaluable samples, >=20 trading days, >=2 regimes, >=95% outcome completeness, <=20% single-symbol share, plus portfolio/cost/capacity and P0-R evidence.
- No Small Live authorization before Gate 0–8 pass.

### W5｜Candidate Strategy Lab
- No active VNext Alpha candidate is currently authorized.
- New idea intake remains allowed, but research volume must not be created merely to fill a backlog.

### W0 Promotion Decision
- PROMOTE_CANDIDATE: **None**
- HOLD: Swing 5D 3-factor challenger; Revenue MoM 5D; Revenue YoY Acceleration 5D; Revenue YoY 5D; Revenue YoY 20D
- REJECT / ARCHIVE: keep current Freeze Registry unchanged
- Production baseline: **unchanged / frozen at Sky V2.1**

### Autonomous execution policy
Within existing authorization, W0 continues to: inventory -> converge -> validate governance evidence -> update Registry -> set next priority. No per-step user approval is required. User intervention is required only for new external credentials/accounts, real-capital or irreversible risk, user-specific 1R/max-position settings, unavailable critical external data, or manual ChatGPT window operations.

## K. W2 PR #79 Review / Merge — 2026-10-25

### Review result
- PR #79 `W2: canonical intraday PIT replay + 10-rule validation framework` — **MERGED**.
- Merge commit: `41fc829d2261e78a559d5fdb7e07446c1c875f8b`.
- W0/P0-G decision: research infrastructure accepted; **no Production trading-rule promotion**.
- Sky Day Trading v1.4 / P0-C MVP Production behavior remains unchanged.

### Accepted W2 research infrastructure
- Intraday PIT Replay Contract
- Fail-closed replay validator
- Canonical 10-Rule Remove-One Ablation
- Walk-forward / Market-Regime stability analysis
- 0.45% / 0.65% cost-stress framework
- W2 end-to-end validation runner
- W2 CI / unit tests

### Governance confirmation
- Research Freeze Registry respected.
- No ARCHIVED_NO_RETUNE family was revived by threshold, Top-N, indicator-period, weight, stop/target or nonlinear-model retuning.
- Missing mandatory PIT evidence results in `DATA_BLOCKED` / HOLD.
- No Day Trading rule is newly classified as Production Stable Rule.
- W2 formal status remains **HOLD**.

### Highest-priority next workstream
**W3｜Intraday PIT Historical Replay Dataset — P0 / Highest Priority**

Formal handoff:
`docs/W3_INTRADAY_PIT_REPLAY_DATASET_PRIORITY_20261025.md`

W3 must build a canonical point-in-time historical decision replay dataset that passes the W2 fail-closed validator before W2 may produce full 10-rule efficacy evidence.

### Updated master-control priority
1. **W3 Intraday PIT Historical Replay Dataset**
2. W4 Shadow/Paper evidence accumulation
3. P0-R portfolio/risk validation
4. Remaining Production hardening / rollback readiness
5. W1 canonical PIT Swing replay when its required data path is ready
6. New alpha research only after the above bottlenecks are materially reduced

## L. Window Execution Directives — 2026-10-25

### Current critical path
**W3A → W2 → W4 → W0**

### Priority map
1. **W3A / P0 Highest** — Intraday PIT Historical Replay Dataset.
2. **W2 / P1 dependent** — Run canonical 10-rule validation only after W3A dataset passes fail-closed validation; until then HOLD / DATA_BLOCKED.
3. **W4 / P1** — Continue Shadow/Paper evidence accumulation to sufficiency gate.
4. **W3B / P1** — Production engineering support for reproducible W3A→W2 pipeline, CI/E2E/runtime/rollback.
5. **W6 / P2** — Execution/microstructure evidence, especially historically reconstructable spread/slippage/fill/liquidity assumptions.
6. **W1 / P3** — HOLD; prepare canonical PIT Swing replay, no duplicate current-universe reruns as new evidence.
7. **W5 / P4** — Intake only; duplicate/low-value screening before new research.
8. **W7 / P4** — Low-intensity global/vendor intelligence; route candidates through W5 and W0.

### Workstream split
- W3A owns Data / PIT / Feature Engineering.
- W3B owns Cloud / Deployment / Runtime / Monitoring / E2E.
- Legacy W3 is deprecated for new work and retained only as history.

### Production governance
- Day Trading v1.4 remains ACTIVE and unchanged.
- Swing V1.0 remains ACTIVE and unchanged.
- W2 remains HOLD.
- No new Stable Production Rule has been authorized.
- No Small Live authorization exists.
- New alpha expansion is lower priority than evidence/data completion.

## M. W3A Coverage Blocker / W5-W7 Adjudication — 2026-10-25

### Verified latest evidence
- W3A status: **ENGINEERING COMPLETE / DATA_BLOCKED**.
- Existing historical 5m artifact: 100 symbols, 2,704,785 bars, period approximately 2023-05-23 through 2026-10-22, export validation PASS.
- Maximum possible symbol coverage versus governed PIT Universe:
  - 2023-12-31: 100 / 1,904 = 5.2521%
  - 2024-12-31: 100 / 1,960 = 5.1020%
  - 2025-12-31: 100 / 2,028 = 4.9310%
  - 2026-09-30: 100 / 2,069 = 4.8333%
- Governance requirement remains >=95%; current artifact is therefore engineering/regression evidence only, not promotion-grade PIT replay evidence.

### W5 / W7 candidate adjudication
PR #93 `W5: refresh W7 inbound adjudication with latest PIT evidence` — **MERGED**.
Merge commit: `efae134bda8318bb018a251e0c679726e0af3e44`.

Formal queue state:
- ACCEPT_FOR_PREREGISTRATION: **0**
- HOLD: **3**

Candidate priority if blockers clear:
1. Overnight-to-First-30m Reversal — HOLD; lowest data threshold among the three, but Gate 0 still fails.
2. Dynamic Futures/ETF/Spot Lead-Lag — HOLD; requires synchronized timestamp/session/stale-index/roll causality contract plus downstream replay data.
3. Broker-Identity / Skill-Conditioned Flow — HOLD; HARD DATA GATE, DO_NOT_BUY NOW until sample/schema/branch lifecycle/PIT mapping/licensing reproducibility are verified.

### Governance decision
- Do **not** promote any of the three candidates to formal Pre-registration yet.
- Do **not** use completed builders/validators/audits as a substitute for >=95% PIT coverage.
- Do **not** buy Broker Flow data now.
- Production remains unchanged.
- W2 remains HOLD / DATA_BLOCKED.

### Updated bottleneck
The system bottleneck is no longer engineering implementation of the W3A replay framework. The bottleneck is **promotion-grade whole-universe synchronized historical intraday data coverage and causal context reconstruction**.

### Updated execution priority
1. **W3A — Resolve promotion-grade whole-universe intraday history / PIT coverage blocker**; produce an evidence-backed source/acquisition/build plan rather than more framework code.
2. **W6 — Define and validate synchronized execution/cross-market timestamp/session/roll causality requirements** needed by Lead-Lag and W2 replay.
3. **W4 — Continue Shadow/Paper prospective evidence accumulation**, because forward evidence can accumulate while historical PIT remains blocked.
4. **W3B — Keep the data/validation pipeline reproducible and ready for larger datasets; avoid unrelated platform expansion.**
5. **W2 — Remain HOLD until the replay dataset passes the fail-closed Gate; no rule efficacy claims.**
6. **W5/W7 — Keep all three candidates HOLD; re-review Overnight first only when data Gate 0 materially improves.**
7. **W1 — HOLD; reuse future PIT infrastructure rather than duplicating data work.**


## N. W0 v1.4 Historical Replay Decision — 2026-10-26

### Formal decision
Historical full-rule replay for `Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP` is **NOT FULLY RECONSTRUCTABLE from the current GitHub SSOT**.

This is a provenance limitation, not a profitability conclusion.

### Evidence state now
- 2023+ PIT Universe: PASS
- corrected whole-universe 5m raw source: PASS
- TAIEX 5m benchmark: PASS
- objective PIT-safe primitives: available
- canonical W2 10-rule frozen providers: incomplete / unresolved
- historical canonical full decision stream: unavailable
- retained historical scanner artifacts: Top-N / context-truncated
- fail-closed v1.4 evidence adapter: merged

### Governance action
W3A is no longer instructed to synthesize missing v1.4 Alpha rules or wait for an undefined replay formula.

Forbidden:
- retrospective threshold reconstruction
- research-only rule substitution
- archived breakout substitution
- outcome-driven inference of historical gate booleans
- claiming historical v1.4 10-rule efficacy without authoritative frozen providers

### W2
Formal status:
**HOLD / HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE**

W2 remains active for:
- future preregistered challengers
- fully frozen strategies with eligible PIT evidence
- OOS / walk-forward / cost / regime / ablation validation when provenance gates pass

### New P0 critical path
1. **W4 — Forward Shadow/Paper evidence accumulation**
2. **P0-R — Portfolio/risk validation**
3. **W6 — Prospective execution/slippage/fill evidence**
4. **W3B — Reproducible forward evidence pipeline / operational hardening**
5. **W0/P0-G — Evidence review and governance**
6. W2 — future challenger validation only when eligible
7. W3A — PIT/data maintenance; no synthetic v1.4 Alpha reconstruction

### Re-open condition
Historical v1.4 full-rule replay may only be re-opened when an authoritative historical source is supplied and verified as:
- `FROZEN_CANONICAL_IMPLEMENTATION`; or
- `HISTORICAL_SNAPSHOT`.

Canonical decision:
`docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md`

Production baseline remains unchanged.

## N. W3A Data Acquisition Path — 2026-10-26

### Verified source options
- Fugle historical minute candles support 1/3/5/10/15/30/60-minute bars from 2023-05-23 for listed/OTC symbols by code; API is authenticated and rate-limited by plan.
- TWSE Data E-Shop provides official all-market historical intraday data. The 5-level order-book product is available from 1992-01-01 and is listed at NT$5,000/month for internal use; order-type data is NT$10,000/month and is not currently required.
- TPEx Data E-Shop provides historical trade files from 2022-11-01; paid official acquisition remains a fallback path.

### Cost-control decision
- First use existing repository Fugle API capability to test whether symbol/date breadth can be expanded without new spend.
- Do not purchase TWSE / TPEx data until zero-new-spend Fugle feasibility is exhausted.
- Do not purchase Broker Flow data.
- Any paid data acquisition requires explicit user approval before purchase.

### New W3A artifacts
- `docs/W3A_INTRADAY_PIT_DATA_ACQUISITION_PLAN_20261026.md`
- `research/probe_fugle_pit_intraday_coverage.py`
- `.github/workflows/w3a-fugle-pit-coverage-probe.yml`

### Probe objective
Use the existing `FUGLE_API_KEY` GitHub Actions secret to probe active TWSE/TPEx and historical-closed PIT members. Measure actual minute-data availability, plan restriction, rate limiting and historical-symbol retrievability before deciding whether official paid data is required.

### Governance
This probe is feasibility evidence only. It cannot authorize W2 validation, formal Pre-registration or Production changes. The >=95% PIT coverage gate remains unchanged.
