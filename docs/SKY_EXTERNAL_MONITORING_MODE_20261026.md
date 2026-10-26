# Sky External Monitoring Operating Mode

Date: 2026-10-26

## Active architecture

- Scheduling / monitoring owner: GitHub Actions and external runtime.
- ChatGPT role: on-demand reader / analyst only.
- Canonical latest snapshot:
  - docs/SKY_EXTERNAL_LATEST_STATUS.json
  - docs/SKY_EXTERNAL_LATEST_STATUS.md
- Routine intraday scans do not send Telegram messages.
- Telegram is reserved for material governance / evidence changes when credentials exist.

## Material Telegram events

A notification is eligible only when one of the following occurs:
- W4 stage changes;
- pipeline enters or exits a failure state;
- W4 sample sufficiency first becomes true;
- promotion-to-governance-review first becomes true.

Ordinary sample-count increments are persisted to GitHub but do not generate Telegram noise.

## Failure-safe behavior

If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is absent, workflows continue normally and
the latest result remains available in GitHub. Missing Telegram configuration must
never block scanner, evidence collection, or Production.

## ChatGPT usage

When the user asks:
- 讀取 Sky 最新結果
- Sky 最新狀態
- W4 現在進度

ChatGPT should fetch docs/SKY_EXTERNAL_LATEST_STATUS.json first and then open linked
evidence only when additional detail is needed.

No ChatGPT automation is required for Sky monitoring.
