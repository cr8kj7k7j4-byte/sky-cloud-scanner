# Sky External Monitoring Architecture

Date: 2026-10-26

## Decision

Sky monitoring and scheduling run outside ChatGPT.

### External execution
- GitHub Actions `scan.yml`: 09:05 / 09:15 / 09:30 / 09:50 / 10:15 Asia/Taipei.
- GitHub Actions `shadow-outcome-backfill.yml`: 14:30 Asia/Taipei.
- GitHub Actions `shadow-promotion-dashboard.yml`: 16:30 Asia/Taipei.
- GitHub Actions `publish-external-status-snapshot.yml`: 16:45 Asia/Taipei.

### Stable result handoff
The final external status is persisted to:
- `docs/SKY_EXTERNAL_LATEST_STATUS.json`
- `docs/SKY_EXTERNAL_LATEST_STATUS.md`

ChatGPT does not need to monitor or schedule these jobs.
When the user opens ChatGPT and asks `讀取 Sky 最新結果`, ChatGPT should read the stable status snapshot from GitHub and analyze it.

## Important limitation

An ordinary external GitHub workflow cannot inject a message into an existing normal ChatGPT conversation by itself. Automatic in-ChatGPT delivery would require a ChatGPT Scheduled/Event task, which this architecture intentionally avoids.

For proactive notification without ChatGPT scheduling, use an external channel such as Telegram/email and keep GitHub as the canonical evidence store.
