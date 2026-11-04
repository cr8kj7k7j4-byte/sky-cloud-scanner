# Sky Realtime Command Contract v1.0

Status: Production command/data-routing contract  
Date: 2026-10-27

## Core rule

All Sky commands that ask for **current state, update, scan, position status, alert state, or full analysis** must refresh the newest obtainable Taiwan-stock market data before producing a decision.

Realtime availability is a **data requirement**, not proof of strategy profitability or Production promotion.

## Canonical data routes

### Whole-market realtime
Use for:
- `Sky 快掃`
- `Sky 快掃更新`
- `Sky 當沖現在掃一次`
- `Sky 當沖快掃`
- `Sky Swing 5D 快掃`
- `Sky Swing 5D 現在掃一次`
- `Sky 波段現在掃一次` → canonical alias of `Sky Swing V1.1｜現在掃一次`; returns intraday BUY / WAIT / REJECT via V1.1 execution overlay
- `Sky 波段快掃` → broad swing candidate scan only
- `Sky Swing V1.1｜現在掃一次` → explicit V1.1 live scan

Pipeline:
1. TWSE + TPEx official current universe.
2. TWSE MIS batched TSE + OTC operational intraday quotes.
3. Record quote coverage and timestamp.
4. Apply the relevant strategy/candidate rules.
5. Deep-dive shortlisted symbols using Fugle single-stock realtime data where available.
6. Never describe MIS OTC as TPEx-official realtime certification.

### Single-stock realtime
Use for:
- `Sky 當沖更新 <symbol>`
- `Sky 波段更新 <symbol>`
- `Sky Swing 5D 更新 <symbol>`
- `Sky 完整分析 <symbol>`
- `Sky 當沖持倉更新 <symbol> ...`
- `Sky 波段持倉更新 <symbol> ...`

Required:
- latest obtainable quote
- source
- timestamp
- no fabricated VWAP/volume/support/resistance when unavailable

### Monitoring realtime
Use for:
- `Sky 持倉`
- `Sky 警戒`

Refresh every monitored symbol/position before calculating status, stop/target proximity, or invalidation state.

### Historical PIT only
Use for:
- `Sky 回測目前模型`
- `Sky 回測 ...`
- `Sky 驗證 ...`

These commands must remain Point-in-Time historical workflows. Realtime data must not replace historical PIT evidence.

## Fail-closed rule

If a Sky command contains `現在`, `更新`, `快掃`, `持倉`, `警戒`, `完整分析`, or `掃一次` but no explicit route exists:
- mark `REALTIME_REQUIRED_UNROUTED`
- do not silently fall back to stale web rankings
- do not produce executable prices from stale data
- add a governed route first

## Strategy governance

- Sky Day Trading v1.4 remains the active formal intraday baseline.
- Sky Swing V1.0 remains active, subject to its exact-rule governance limitation.
- Sky Swing 5D remains research-only/HOLD unless promotion gates change.
- Sky Swing V1.1 remains PREREGISTERED_CHALLENGER / NOT_PRODUCTION.
- Connecting realtime data does not alter Alpha rules, thresholds, stops, targets, or promotion status.


## Canonical presentation

Current-state Sky outputs use `docs/SKY_MOBILE_RESULT_TABLE_V1_0.md` as the primary candidate table:
`股票｜現價｜方向｜多方評分｜空方評分｜買進觸發｜最高接受價｜停損／失效｜分類｜現在動作`.

Missing governed levels remain `—`; presentation must not invent prices just to fill the table.


## Chat execution bridge

For `Sky 波段現在掃一次` / `Sky Swing V1.1｜現在掃一次`:
1. GitHub Actions maintains a Swing V1.1 whole-market live scan every 5 minutes during Taiwan market hours.
2. Chat reads the latest successful scan artifact / summary as the canonical whole-market candidate pool.
3. Chat then refreshes shortlisted symbols with connected Fugle realtime single-stock quotes when available.
4. Public web search is fallback context only and must not replace the canonical live-scan + Fugle path for executable intraday judgments.
5. If the latest live scan is stale or unavailable, fail closed and disclose the stale timestamp.


## Update command presentation

任何包含「更新」的 Sky 指令，完成即時資料刷新後，都必須先使用 `SKY_MOBILE_TABLE_V1_0` 10 欄格式輸出主決策表。持倉更新可在表格後追加成本／張數／損益等欄位。


## Mandatory single-stock realtime bridge

For every single-stock current-state command:
- `Sky 當沖更新 <symbol>`
- `Sky 波段更新 <symbol>`
- `Sky Swing 5D 更新 <symbol>`
- `Sky 完整分析 <symbol>`
- position-update variants

Execution order is mandatory:
1. Call connected Fugle realtime quote for the requested symbol.
2. Record returned quote timestamp / lastUpdated.
3. Use the returned live price, intraday high/low, volume and available bid/ask as current-state evidence.
4. Only after the realtime quote succeeds may analysis and presentation proceed.
5. Public web data may supplement news/background only; it must not replace the live current price.
6. If Fugle realtime quote fails or permission is unavailable, fail closed as realtime data unavailable. Do not fall back to a stale prior-close or older web snapshot as if it were live.

This requirement applies even if an older public source appears newer than the last completed daily market dataset.


## Single-stock on-demand cloud bridge — 2026-11-03

User intent:
- `Sky 當沖更新 1569`
- `1569 濱川 當沖要怎麼操作，請給我多空評分、最高接受價與停損`

The router maps both to `SINGLE_STOCK_REALTIME`. Chat MUST query the connected Fugle realtime-quote tool first; the on-demand GitHub counterpart is `.github/workflows/sky-single-stock-realtime.yml`, with `workflow_dispatch.symbol` (4–6 digits). This workflow is manual/on-demand, not a streaming subscription or a new scheduled scan. It reads the repository secret `FUGLE_API_KEY`; the ChatGPT connector connection does not grant this secret or entitlements.

Cloud evidence collector: `python -m src.sky_single_stock_realtime --symbol 1569`.
Cloud evidence output: `output/single_stock/1569.json` uploaded as a workflow artifact.
Cloud status `REALTIME_QUOTE_VERIFIED` requires same-day valid trade timestamp, age <=120s, not future by more than 30s, positive last trade, and `canDayTrade=true`. All failed gates MUST exit nonzero and publish a fail-closed artifact; the model never treats a completed action alone as a buy signal. Record source, last-trade time, last-update, current price, open/high/low, cumulative volume, best bid/ask and market eligibility. This is a snapshot, never a streaming or guaranteed exchange-latency claim.

2026-11-03 Fugle connector permissions inspected:
- Directly verified single-symbol quote: 1569 TPEx, quote + bid/ask + volume + day-trade eligibility.
- Accessible content-spec metadata, but contents not yet validated for: FCNT000013 recent 3-day prices, FCNT000002 5-year prices, FCNT000003 margin, FCNT000005 institutions, FCNT000009 brokers, FCNT000004 material disclosures, FCNT000153 15-year prices, FCNT000154 adjusted history.
- Connector entitlement and GitHub raw MarketData REST key entitlement are independently verified; do not infer one from the other.
- Availability of 1m/5m intraday candles, full tick sequences, indicator-ready VWAP, historical depth, rate quotas and cloud scheduled runs MUST be separately verified before they become required decision inputs.

A verified quote alone does NOT authorize A+ grading, a numerical bull/bear score, max entry, stop, target, net RR or position size. Require the governed P0-C setup/trigger + multi-timeframe liquidity and P0-R cost/risk rules. Missing evidence remains `—`/WAIT, never backfilled from prior close. This bridge is a data-source engineering change ONLY: no production strategy promotion, no automatic order placement, and no risk-rule alteration.


## 2026-11-04 W3A consolidated realtime provenance supplement

Authoritative matrix: `docs/SKY_UNIFIED_REALTIME_SCOPE_20261104.md`.

- `Sky 全市場即時行情` and `Sky 全市場掃描` require proof of actual current-session executed prices across TWSE+TPEx. An official full-market **daily** universe is not intraday full-market execution data.
- `Sky 當沖空方研究 掃一下` is a **research-only blocked** route until independent live short-execution eligibility and model evidence are verified.
- `Sky 持倉監控` uses individual fresh quotes for the currently verified portfolio; no inferred historical holdings.
- `Sky Swing V1.1｜現在掃一次` uses a frozen D-close cross-section and live **candidate-only** quotes. Its previous `operational_full_market_scan` label may not be used to assert whole-market realtime prices; the data scope is explicit.
- A quote's `closePrice` / `lastUpdated` without a corroborating executed trade price and trade timestamp is not sufficient for live execution.
- Historical validation must continue using true PIT data; combining live evidence does not reset historical OOS or lift research freezes.
- GitHub REST bulk snapshot entitlement remains independently blocked by HTTP 403 in the last verified runtime. The connected ChatGPT Fugle realtime quote does not grant that secret scope.
- The 2026-11-04 verified MIS executed quote coverage was 90/1,985 (4.53%). Until a legitimate full-market source is validated, all whole-market realtime commands fail closed or explicitly report split-scope research. Do not buy a data plan without verifying entitlement/need.
