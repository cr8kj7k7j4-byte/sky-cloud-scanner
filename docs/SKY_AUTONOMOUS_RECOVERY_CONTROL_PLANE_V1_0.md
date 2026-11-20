# Sky Autonomous Engineering Recovery — W0 proposal (research-only)

Status: DESIGN_AND_MONITOR_FIX_PENDING_CI; NOT an active general-purpose repair agent. Owner: W0 / P0-G.
This extends existing governed controller `scripts/sky_governed_auto_repair.py` and the existing ten-minute watchdog; do **not** launch another independent repair daemon.

## Problem confirmed on 2026-11-12
The watchdog was polling legacy #506/#510 and describing five-minute cadence; newer key blockers #531/#536 were missing.
The governed controller is an exact-match patcher for one workflow or a separate isolated smoke fixture, not a broad code engineer.
A green workflow, PR metadata, or available Artifact ZIP is NOT end-to-end repair acceptance.

## Intended end-to-end state machine
DISCOVER → DEDUP → CLASSIFY → PLAN → APPLY_BOUNDED_PATCH → TEST_OFFLINE → SECURITY_REVIEW → CI_SAME_SHA → ARTIFACT_EXTERNAL_READBACK → E2E_REAL_DATA → W0_DECISION → CLOSE.
Every transition persists immutable run id, PR, SHA, version, error classification, input provenance, action/patch hash, tests, artifacts and output in a durable repair ledger.
HOLD, BLOCKED_EXTERNAL, REJECT and ACCEPTED are different terminal/paused states. Progress is actual evidence transitions, never number of scheduled triggers.

## Five connected functional lanes, not five concurrent writers
1. Ingest: monitor #508, #511, #512, #531, #536 and current main, fresh CI jobs/logs, owner decisions and artifact receipt. Each work item is keyed by (repository, PR, exact head SHA, failure fingerprint).
2. Diagnose: classify code/permission/source/secret/quota/market-clock/integration/data-provenance/CI failure. Infer nothing from green CI alone.
3. Execute: only deterministic, owner-approved file+change allowlists; acquire a single orchestration lease and branch-per-SHA idempotency key. Unknown or semantic changes become an evidence-backed Draft PR for human decision, NOT blind automatic modification.
4. Verify: run offline PR tests and same-SHA CI; externally download, hash and read artifacts; verify consumer path; block on schema mismatch, absent timestamps or missing ledger events. No fabricated fills or market-data certification.
5. Govern: write a concise actionable receipt distinguishing APPLIED, TEST_PASS, ARTIFACT_VERIFIED, DATA_VERIFIED, E2E_PASS and ACCEPTED. Only explicit W0 owner decision can merge governance-sensitive research or Production.

## Scheduling and market windows (Asia/Taipei)
Existing `sky-recovery-watchdog.yml` cron is */10 UTC minutes best-effort, not an SLA. GitHub cron can be delayed or skipped.
Weekdays 09:00–13:30: read-only code monitoring and ONLY separately authorized market-session TWSE/TPEx executed-trade timestamps, completed 5m K bars, source latency / coverage, via existing scanner paths and official TWSE calendar. If closed/holiday, skip paid market verification.
Outside session: code refactor, unit/integration tests, PR creation, Artifact and bridge consumer readback, simulated PAPER_ONLY ledger tests, source configuration diagnosis, W0 review.
Session detection by weekday+clock is not a trading-calendar guarantee. Off-market tests must not interfere with required live-market proof.

## Provider and cost policy
Fugle NT$1,499 monthly subscription is a fixed plan reported by owner; request caps and overage semantics remain NOT VERIFIED. Use existing entitlement fully within real limits; no added services or fees. #536 must guard four paid workflows with valid reservation/readback, avoiding duplicate calls without blocking legitimate scans.
Distinguish Fugle provider charges from GitHub Actions usage; log request counts, rate-limit response, provider error and API reservation IDs; never expose API keys.

## Repair worklist and acceptance gates
| PR | Window | Required proof |
|---|---|---|
| #536 | Off-market | All paid entrypoints inventory, cross-runner contention, one legitimate admission, rejected duplicate, paid calls not triggered on rejection |
| #531 | Off-market | Existing chat bridge connects real same-run Artifact, source and capture timestamps verified externally |
| #508 | Off-market, then real data verification | Actual precommitted signal, completed OHLC with source, paper order/fill/stop/ledger/cost/RR events; no invented executions |
| #511 | Market session | TWSE/TPEx independent eligible universe coverage, per-symbol actual execution timestamps, missing/duplicate classifications |
| #512 | Market session | Real completed 5m bar evidence, no future/incomplete candles, integration from canonical scanner with run receipt |
| #523 | Off-market | Required check evidence-preflight enforced in main Ruleset, readback and owner approval |

## Engineering safety invariants
Never modify Production strategy thresholds, trade signals, no-order gate, P0-R limits or risk/cost profile automatically. No automatic orders, no auto Production promotion, no secret access from untrusted PR, no fork write tokens, no untrusted code with privileged credentials. Limit auto-patch to preapproved deterministic code transformations; require regression tests and human-controlled PR merge for risk/strategy changes. Global lease avoids overlapping repairs; retries capped; repeated failed fingerprint gets cooling period and BLOCKED. Roll back only via proven safe reversible commit plus tests, otherwise HOLD.
GitHub App/Actions permissions and paid provider access are checked before dispatch. If external permission or credentials are missing, log one precise request for minimum owner action and do not loop.

## Exit conditions
A module is COMPLETE only after same-SHA CI, real run, content-level external Artifact readback, user-facing consumption and W0 approval. Study-stage integration readiness is different from formal profitable trading acceptance.
Formal research promotion remains subject to docs/SKY_VALIDATION_PROTOCOL_V1_0.md including >=200 evaluable trades, >=20 true forward trading days, >=2 regimes, outcome completeness >=95%, concentration <=20%, as well as execution cost and portfolio gates. Do not compress real future days via repeated scans.
No overall closure until all worklist gates and evidence have been verified. No claims of unsupervised repair coverage before a genuine nonfixture source failure has been repaired and reverified through the entire chain.

## Implementation milestones
M0 (this PR): accurate backlog and work-window reporting with no paid calls and no autonomous code writes.
M1: durable idempotent issue ledger, evidence hashes and artifact readback test on existing watchdog.
M2: expand existing governed controller with narrow approved patch recipes only, CI/Artifact confirmation, rollback and operator escalation.
M3: live-market authorized workflows after #536 gates, exchange-calendar/snapshot validation and PAPER_ONLY signal/ledger E2E.
M4: W0/P0-G documented research-only completion. No Production upgrade.
