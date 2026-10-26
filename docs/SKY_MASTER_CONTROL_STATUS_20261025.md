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

## O. GitHub Actions Runner Queue Blocker — 2026-10-26

### Observed fact
- W3A Fugle PIT Coverage Probe run #40228265013 remains `queued`.
- Job exists but has `runner_id = 0`, empty runner name and no executed steps.
- Repository currently has no `in_progress` workflow runs, while multiple unrelated workflows are also queued.
- Therefore this is classified as **ACTIONS_EXECUTION_BLOCKED**, not a Fugle/data failure.

### Governance consequence
- Do not mark Fugle feasibility PASS or FAIL until the probe actually receives a runner and executes.
- W3A remains ENGINEERING COMPLETE / DATA_BLOCKED.
- W2 remains HOLD / DATA_BLOCKED.
- No Pre-registration or Production status changes.

### Prepared fallback
- The probe script and acquisition plan are committed and can run unchanged on any environment with Python + requests + `FUGLE_API_KEY`.
- If GitHub-hosted Actions remains unavailable, execution may be moved to an already-authorized runtime (e.g. existing Cloud/production environment) only if no new credential, paid service, or irreversible deployment is required.


## P. Automated Recovery Update — 2026-10-26

### Recovery result
- Core CI / governance / runtime tests: **HEALTHY**.
- Sky Premarket Intelligence scheduled run: **SUCCESS**.
- W3B production hardening and canonical P0-C / P0-R / P0-O / PMS / P0-L / P0-G checks: **SUCCESS**.
- W1 Swing W3 Data Handoff Gate: **SUCCESS** after artifact repair.
- Failed Swing PIT shard from run #40252311154 has been re-run as attempt 2; this is cleanup only and does not change strategy status.
- The earlier repository-wide GitHub Actions queue condition is no longer classified as a global outage because newer scheduled and PR workflows are executing successfully.

### Normal-operation classification
- Production baseline remains **ACTIVE / UNCHANGED**.
- No Production strategy semantics changed during recovery.
- W4 current state is **WAITING_FOR_FIRST_ELIGIBLE_SCAN / HEALTHY**, not a system failure. Zero eligible forward samples is a sample-timing state, not an outage.
- W2 historical v1.4 full-rule replay remains intentionally closed because provenance is insufficient. This is a governance constraint, not an operational incident.
- W3A whole-universe historical intraday coverage remains a data-coverage blocker. Zero-new-spend paths must be exhausted before any paid acquisition request.

### Canonical operating path after recovery
1. Intraday scheduled scans / Shadow snapshots.
2. Same-day outcome completion.
3. W6 forward execution evidence.
4. W4 sample-sufficiency dashboard.
5. P0-R forward risk evidence.
6. W3B runtime hardening / E2E.
7. W0 / P0-G governance review.

### Human action
No immediate user action is required.
User intervention remains required only for:
- paid data acquisition;
- new external credentials/accounts;
- irreversible Production changes;
- real-capital activation;
- user-specific 1R / max-position settings.

### Do-not-do
- Do not restart historical v1.4 rule reconstruction by inference.
- Do not treat zero W4 forward samples as an outage.
- Do not buy broker-flow / TWSE / TPEx historical products until existing free/authorized acquisition paths are exhausted.
- Do not add new broad workstreams while forward evidence accumulation is the critical path.


## O. External Telegram Notification Baseline — 2026-10-26

### Verified operational state
- GitHub Actions → Telegram delivery path: **VERIFIED / ACTIVE**.
- Repository secrets for Telegram delivery are configured and readable by GitHub Actions.
- End-to-end live smoke test: **PASS**.
- One-time smoke-test workflow removed after verification.
- Routine per-scan Telegram notifications: **DISABLED** to avoid noise.
- Telegram purpose: **material status changes only**.
- User-visible Telegram notifications: **Traditional Chinese first**; machine-facing canonical status codes may remain English internally.
- ChatGPT does **not** own monitoring schedules. GitHub Actions / external infrastructure owns recurring execution.
- ChatGPT role remains **on-demand reader / analyst**. Canonical user instruction: **「讀取 Sky 最新結果」**.

### Material notification triggers
Current baseline includes:
1. W4 stage change.
2. Pipeline entering or exiting failure / incomplete-evidence state.
3. W4 sample sufficiency first becomes true.
4. Promotion-to-governance-review first becomes true.

### Security / governance
- Telegram token must remain in repository secrets or equivalent secret store only.
- No token may be committed to source, docs, logs, issues, or PR text.
- Notification setup does not change Alpha logic, Production trading rules, P0-C, P0-R, or promotion status.

Canonical record:
`docs/SKY_TELEGRAM_NOTIFICATION_STATUS_20261026.md`


## P. Telegram All-Events Mode — 2026-10-26

### User directive
Telegram notification scope is expanded from material-status-only to **ALL EVENTS MODE** for `sky-cloud-scanner`.

### Coverage
- All GitHub Actions workflow completions, regardless of conclusion.
- Push.
- Pull Request lifecycle events.
- Issue events and comments.
- PR reviews and review comments.
- Release.
- Deployment status.
- Branch/tag create/delete.
- Fork / Star.
- Discussions and discussion comments.
- repository_dispatch / workflow_dispatch.

### Safety / recursion control
- The Telegram notifier excludes its own workflow name from `workflow_run` matching to prevent recursive self-triggering.
- Secrets remain in GitHub Actions repository secrets only.
- User-visible messages remain Traditional Chinese first.

### Governance impact
- Notification policy only; no Alpha, P0-C, P0-R, Production, risk, or promotion-rule change.
- Existing detailed material alerts may coexist with generic workflow-completion alerts.

Canonical workflow:
`.github/workflows/telegram-all-github-events.yml`

Canonical status:
`docs/SKY_TELEGRAM_NOTIFICATION_STATUS_20261026.md`

## P. Fugle Probe Round 2 / Historical-Window Fix — 2026-10-26

### Round 2 result
GitHub Actions run #40263853713 completed successfully after retry/backoff hardening.

Observed:
- Active sample: 40 / 40 successful = **100%**.
- Historical-closed sample: 2 / 10 successful = 20%.
- No remaining 429 failures after retry/backoff.

### Important correction
The 20% historical-closed result is **not yet valid evidence of historical-symbol coverage failure** because the probe queried the global September 2026 window even for already-delisted symbols. A post-delisting 404 does not establish that historical bars are unavailable during the symbol's actual listing period.

### Corrective action
- Probe logic updated so HISTORICAL_CLOSED symbols are queried within their own effective listing interval, using a 30-day window ending at `listed_to`.
- Commit: `a4140ec1579da8b9ef8751c7d03cc85540d1777d`.
- Third probe triggered: GitHub Actions run #40272554958.

### Governance
- Active-symbol Fugle feasibility is now strong at the sampled level.
- Historical/delisted coverage remains UNKNOWN pending the corrected third probe.
- Do not escalate to paid TWSE/TPEx acquisition until the corrected historical-symbol probe is complete.
- W3A remains ENGINEERING COMPLETE / DATA_BLOCKED.
- W2 remains HOLD / DATA_BLOCKED.

## Q. W0 Full Status Refresh — 2026-10-26

### W3A Fugle feasibility round 3
GitHub Actions run #40272554958 completed successfully after correcting historical-closed query windows.

Observed sample result:
- Active symbols: 40 / 40 OK = **100%**.
- Historical-closed symbols: 10 / 10 OK = **100%** when queried inside each symbol's effective listing interval.
- Overall: 50 / 50 OK = **100%**.
- No 429 failures remained after retry/backoff hardening.

Interpretation:
- Fugle is now a credible zero-new-spend acquisition path for a broader PIT historical intraday backfill.
- This sample does **not** establish the formal >=95% whole-universe PIT gate.
- Next eligible W3A action is to expand from feasibility sample to a materially larger PIT-universe acquisition/coverage test, then to full governed-universe backfill if capacity and coverage remain acceptable.
- Paid TWSE/TPEx acquisition remains fallback only; no purchase authorized.

### W4 latest forward-evidence state
Latest Shadow Promotion Dashboard run #40298299983 completed successfully but reports:
- status: **WAITING_FOR_FUTURE_SAMPLE**
- eligible successful scan runs: **0**
- samples remaining: 200
- trading days remaining: 20
- regimes remaining: 2
- outcome completeness gap: 0.95
- promotable_to_governance_review: false
- production_eligible: false

Therefore W4 infrastructure is healthy, but usable forward evidence has not yet accumulated.

### Open PR governance inventory
Open PRs are not formal Registry state until W0/P0-G review and merge.
- PR #149: W5/W2 Baseline C 'exit immediately below daily open' — OPEN, not merged; no Production change authorized.
- PR #80: W3 canonical PIT adjusted daily Swing dataset — DRAFT, not merged.
- PR #100: W3 canonical PIT daily Swing dataset v2 — DRAFT, not merged.

### Current formal state
- Day Trading v1.4: ACTIVE / unchanged.
- Swing V1.0: ACTIVE / unchanged.
- W1: HOLD.
- W2: HOLD / DATA_BLOCKED pending promotion-grade replay dataset.
- W3A: ENGINEERING COMPLETE; Fugle feasibility PASS at 50-symbol sample level; formal whole-universe data gate still OPEN.
- W3B: ACTIVE support / no Alpha changes.
- W4: WAITING_FOR_FUTURE_SAMPLE; 0 eligible scan runs in latest dashboard.
- W5: ACCEPT_FOR_PREREGISTRATION = 0; HOLD = 3 for current W7 inbound queue.
- W6: no formal Production-changing result registered.
- W7: low-intensity intelligence; no direct Production path.
- Small Live: NOT AUTHORIZED.

### Current critical path
1. W3A expand Fugle PIT coverage test toward governed whole-universe coverage.
2. W2 remains blocked until the dataset passes fail-closed governance gates.
3. W4 must start accumulating eligible forward scans/samples.
4. W0 reviews open research PRs separately; none are formal until accepted.


## Swing V1.0 exact-rule specification debt — 2026-10-26

- W3 canonical PIT daily data: PASS.
- W1 data readiness: READY_FOR_CANONICAL_SWING_REPLAY.
- W3→W1 handoff: PASS.
- Production Swing V1.0: ACTIVE / unchanged.
- W1: HOLD.
- Blocking gate: BLOCKED_EXACT_RULE_SPEC.
- W0 decision: current SSOT does not contain a complete executable Swing V1.0 rule specification; proxy research may not be substituted.
- Formal decision: `docs/SKY_SWING_V1_EXACT_RULE_GOVERNANCE_DECISION_20261026.md`.
- Resume only after exact frozen rule specification is recovered/governed from contemporaneous pre-result evidence.
