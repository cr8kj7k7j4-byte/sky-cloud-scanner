# Sky Telegram Notification Status — 2026-10-26

## Status
**VERIFIED / ACTIVE — ALL EVENTS MODE**

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
- Repository event notifications are enabled broadly: push, PR, Issue, comments/reviews, Release, Deployment, branch/tag create/delete, fork/star, Discussions, repository dispatch, and manual workflow dispatch.
- All GitHub Actions workflow completions are sent to Telegram regardless of success, failure, cancellation, or other conclusion, excluding the notifier workflow itself to prevent recursion.
- Existing detailed material-status alerts may still be emitted by their owning workflow; therefore a material change can legitimately produce both a workflow-completion notification and a detailed status notification.
- ChatGPT does not own Sky monitoring schedules. GitHub Actions / external infrastructure owns recurring execution.
- ChatGPT remains an on-demand reader / analyst. The canonical on-demand instruction is: 「讀取 Sky 最新結果」.

## Notification policy
Telegram is now configured in **ALL EVENTS MODE** for this repository.

Coverage includes:
1. Every GitHub Actions workflow completion.
2. Push events.
3. Pull Request lifecycle updates.
4. Issues and comments.
5. PR reviews and review comments.
6. Releases.
7. Deployment status changes.
8. Branch/tag create and delete.
9. Fork and Star events.
10. Discussions and discussion comments.
11. repository_dispatch and workflow_dispatch.

Existing domain-specific material alerts remain allowed for richer context.

This mode intentionally produces substantially more Telegram traffic than the prior material-only baseline.

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
