# Sky Fast Report Gateway V1 — Mobile commands

Status: CODE_READY / NOT_DEPLOYED / RESEARCH-ONLY. This is a READ-ONLY snapshot gateway, not an API server, cloud migration, strategy promotion or proof of realtime quotations.

## Why
Multiple separate GitHub scans may duplicate expensive source reads. The first safe speed improvement is to distinguish **read latest published status** from **start new market scan**. This file reader never calls TWSE/Fugle, never dispatches a workflow, and never places orders.

## Commands
| User command | Behavior | Live trading |
|---|---|---|
| Sky 系統快報 | Read latest already-published system health status | No |
| Sky 全市場快報 | Read latest already-published all-market status | No |
| Sky 模型驗證快報 | Read latest model-validation status if published | No |
| Sky 證據快報 | Read latest W4 published dashboard status | No |
| Sky 高速狀態 | Alias for Sky 系統快報 | No |
| Sky 高速全市場 | Alias for Sky 全市場快報 | No |
| Sky 多空最佳機會掃描 | Routes to research-only blocker until PR #270 and gates validated | No |

Command implementation: `python -m src.sky_fast_report_gateway --command 'Sky 全市場快報'`.
Artifact: `output/fast_reports/latest.json`.

Old snapshots, missing reports, timezone ambiguity, no verified quote coverage and untested short eligibility must never become live trade advice. A published report timestamp is not an exchange last-trade timestamp.

## Deployment & performance prerequisites
1. Establish official Workflow/Run inventory and overlapping TW time schedules (the 2026-11-04 status identified 22 workflows and seven attention/unverified).
2. Profile per-run queue duration, market-fetch time, compute, writing, notifications, retries and market API rate-limit.
3. Design one producer, many consumers: one session-scoped market snapshot with source, exchange timestamps, quality flags, per-market coverage and TTL; derive daytrading, short research and swing outputs from the same immutable snapshot.
4. Deploy cloud worker to existing GCP only after project/service/account, billing, secrets, access and network are verified. No secrets in GitHub artifacts. Cloud Run worker requires actual verified deployment and read-back evidence.
5. Expose authenticated report read endpoint or approved app connector for ChatGPT; merely adding a Python file does not create ChatGPT integration.
6. Shadow compare legacy vs shared-snapshot outputs and measure p50/p95 latency, quality and cost before disabling a duplicate GitHub schedule.
7. W0/P0-G approval required for Production modifications; short strategies remain research-only.

## Explicit limitations
This is a **performance infrastructure candidate**, not a claim of faster benchmarks or realtime whole-market coverage. No duplicate Workflow was disabled. Existing v1.4/Swing Production untouched.
