# P0-A｜低融資維持率反彈警戒（RESEARCH_ONLY）

**Not production. Does not place orders. Does not alter ACTIVE scanner or existing workflows.**
As of 2026-11-08, credentials, FinMind Sponsor access, real API success, persistent worker hosting, mobile Telegram delivery and real-session latency are **NOT VERIFIED**.

## Data and eligibility
- FinMind `TaiwanStockMarginMaintenance` (Sponsor) is **EOD estimated** margin maintenance, not a broker's actual account maintenance ratio; select previous trading day's stocks with `margin_maintenance < 130` and `margin_balance >= 100` lots.
- FinMind `taiwan_stock_tick_snapshot` (Sponsor) ~10-second snapshots, all stocks via blank `data_id`. Screened list must be refreshed each session.
- Trigger is 3 **distinct, time-increasing observed snapshots**, each `TickType == 1`, monotonically higher prices and cumulative volume, >=0.7% price gain and >=10 lots between first/last, bid-ask spread <=0.5%, quote age <=35s, within 90s, dedupe 10min per code.
- Snapshot samples cannot prove every intervening trade was buyer initiated; only a research alert. Thresholds are initial hypotheses, not backtested profitable settings.

## Run only on controlled persistent worker
```bash
export FINMIND_TOKEN='<in secure secret manager>'
export TELEGRAM_BOT_TOKEN='<in secure secret manager>'
export TELEGRAM_CHAT_ID='<in secure secret manager>'
export MARGIN_WATCH_POLL_SECONDS=15
export MARGIN_WATCH_DRY_RUN=1
python -m unittest tests.test_margin_rebound_watch -v
python -m research.margin_rebound_watch
```
Default is dry-run; to actually deliver notifications explicitly set `MARGIN_WATCH_DRY_RUN=0` after verified access and smoke tests. The script exits after market hours and on weekends. **No scheduler has been added**, because GitHub Actions cron (>=5min, possible queue delay) does not meet first-opportunity alerting SLAs and an always-on worker with restart management has not yet been validated.

## Required gates before any activation
1. Verify FinMind Sponsor data entitlement and API response, observe freshness and all-stock field coverage; independently measure missing/late data.
2. Confirm Telegram bot and the mobile user's chat are linked, send dry-run then test real notification, measure end-to-end delay and delivery/retries.
3. Configure a protected worker (secrets, deployment, watchdog, trading calendar, restart, durable cooldown state and no overlapping sessions). Current prototype holds cooldown in RAM; restart can duplicate alerts.
4. Replay days with timestamped point-in-time quotes; measure precision/recall, false alarms, and compare cost-after-risk results; W0/P0-G review before any formal trading signal.
5. Do not enable unrelated paused Sky workflows or auto-trading.

Official FinMind references:
- https://finmind.github.io/tutor/TaiwanMarket/Chip/
- https://finmind.github.io/tutor/TaiwanMarket/RealTime/
