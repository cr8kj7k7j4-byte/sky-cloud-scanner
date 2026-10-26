# Sky Telegram Notification Status — 2026-10-26

## Status
**VERIFIED / ACTIVE**

## Scope
This document records the external notification state for all Sky workstreams W0–W7.

## Verified facts
- GitHub Actions → Telegram delivery path has been end-to-end tested successfully.
- Repository secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured and readable by GitHub Actions.
- The Telegram bot private-chat path has been initialized by the user.
- A live smoke test delivered successfully to the user on 2026-10-26.
- The one-time smoke-test workflow was removed after verification.
- User-visible Telegram notifications are Chinese-first.
- Internal system status codes may remain English for machine logic and governance traceability.
- Routine per-scan Telegram delivery remains disabled to avoid notification noise.
- Telegram is reserved for material status changes only.
- ChatGPT does not own Sky monitoring schedules. GitHub Actions / external infrastructure owns recurring execution.
- ChatGPT remains an on-demand reader / analyst. The canonical on-demand instruction is: 「讀取 Sky 最新結果」.

## Material notification policy
Telegram may notify when one of the following occurs:
1. W4 stage changes.
2. Pipeline enters or exits a failure / incomplete-evidence state.
3. W4 sample sufficiency is reached for the first time.
4. Promotion-to-governance-review gate is reached for the first time.
5. Future W0/P0-G-approved material alert conditions are added.

Routine scan results, ordinary heartbeat runs, and unchanged status snapshots should not generate Telegram messages.

## Language policy
User-visible Telegram alert text should be Traditional Chinese whenever practical.
Professional abbreviations such as W4, P0-R, PF, RR may remain unchanged.
Machine-facing enum/status values remain canonical English codes internally.

## Security policy
- Never store Telegram tokens in source files, logs, docs, issues, PR bodies, or chat transcripts.
- Tokens must be stored only in repository secrets or equivalent secret stores.
- Any token exposed outside the secret store must be revoked and replaced.
- Chat ID and bot token must not be conflated.

## Production impact
No trading strategy, Alpha logic, P0-C decision rule, P0-R rule, or Production promotion state was changed by this notification setup.

Production baseline remains:
- Sky V2.1
- Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP
- Sky Swing V1.0

## Canonical related files
- `.github/workflows/publish-external-status-snapshot.yml`
- `docs/SKY_EXTERNAL_MONITORING_MODE_20261026.md`
- `docs/SKY_EXTERNAL_LATEST_STATUS.json`
- `docs/SKY_MASTER_CONTROL_STATUS_20261025.md`

## Cross-window directive
All Sky workstreams W0, W1, W2, W3A, W3B, W4, W5, W6, and W7 should treat this document as the current notification-operating baseline unless superseded by a later W0/P0-G governance record.
