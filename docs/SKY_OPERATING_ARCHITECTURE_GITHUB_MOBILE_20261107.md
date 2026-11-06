# Sky Operational Decision — GitHub-first Mobile Delivery (2026-11-07)

Status: **USER_CONFIRMED / OPERATING_ARCHITECTURE**. This note records an operating preference, **not** a Production model or data-provider promotion.

## Confirmed primary architecture
**GitHub Actions + existing legitimately accessible data sources + Sky analysis + mobile report and notification.**
Goal: user should not need the home PC or ongoing manual PowerShell sessions for normal operation.

## Scope and priorities
1. **STOP NOVA CLOUD EXPANSION.** No new Cloud Run / GCP deployment, secret copy, Nova hosted trading-certificate integration, new vendor credential, or new Nova work stream without a new explicit user decision. Preserve existing Nova local-test evidence and draft PR #300 as non-production research; do not merge it merely to complete tasks.
2. Return to the existing production scanner on `main`. No reimplementation, no account purchases by default, no surprise new ChatGPT schedules.
3. Audit actual five-scan GitHub Actions operations and output: Asia/Taipei 09:05, 09:15, 09:30, 09:50, 10:15, trading day gate, trigger timestamp, runtime, log, artifact, completeness, and fail-closed behavior. Defined cron is not evidence of runs being timely.
4. Audit available and lawful TWSE/TPEx/Fugle quote sources, exact entitlement, source timestamps, TSE versus OTC coverage, executed-trade evidence; MIS OTC is operational fallback not TPEx's complete official real-time feed. No invented coverage. If feed is stale/incomplete, no new trading signal.
5. Verify mobile rendering and notifications end-to-end: latest report generated, hosted access from phone, recipient delivery / failure alert, duplicate suppression, retry and recovery. Report status separately for program success, data quality, report generation, signal validity, and strategy proof.
6. Repair upstream operational defects in place, prioritize risk and stability; no model/Production rule promotion or automated orders without W0/P0-G.
7. Retain research governance: `SKY_SYSTEM_REGISTRY_V2_1.md`, `research/RESEARCH_FREEZE_REGISTRY.md`, `docs/SKY_VALIDATION_PROTOCOL_V1_0.md`. Profitability evidence is a separate gate.

## Existing environment confirmed by code review (not live-verification)
- `.github/workflows/scan.yml` defines five scan slots.
- `src/diagnose_sources.py` probes official universe, stratified MIS samples and Fugle data, includes quality flags; snapshot endpoint may be plan-restricted.
- `docs/SKY_EXTERNAL_LATEST_STATUS.json` last checked was generated 2026-11-06T09:36Z; historical status only. Do not treat as live 2026-11-07.
- GitHub connector access available for repo code and commit-associated PR runs. **Scheduled workflow runs, delivery and live artifact acceptance require direct execution evidence**. They have not been fully established by this note.
- `Sky Nova 行情介接續辦` ChatGPT automation has been disabled at user direction to stop cloud expansion. Existing independent Sky speed/recovery schedule is not changed here.

## Next evidence requests (no user action by default)
Read recent scheduled run/job records and artifacts, source quality status per exchange, latest published mobile report links and notification delivery outcomes. Label any unavailable evidence `待確認`; do not claim healthy execution from workflow YAML alone.

## Explicit restrictions
No broker PFX/password/token in GitHub; no new cloud stack; no automated orders; no claim of validated positive after-cost expectancy; no Production promotion.
