# Fugle Chat Quote Bridge — initial integration contract (2026-10-28)

Status: ROUTING ALIAS / REVIEW ONLY. This file does not attest to an autonomous market-data service, a deployed cloud integration, or a validated trading strategy.

## Verified in the connected ChatGPT environment
- Fugle-Stock `get_realtime_quote(symbolId)` returned 2026-10-28 close snapshots for 6695, 1717, 5425, and 9914.
- Returned fields included `lastPrice`, `lastUpdated`, `isClose`, day high/low, cumulative volume, five-level `bids`/`asks`, and security/day-trade status.
- These connector calls are available in ChatGPT, **not** automatically from GitHub Actions or Cloud Run. Separate authorized Fugle API credentials/network access would be needed for unattended scanner ingestion.

## Command
`Sky 富果當沖更新 <symbol>` is a strict alias to the existing `SKY_SINGLE_STOCK_UPDATE` command family. It does not modify P0-C v1.4 scoring, position sizing, P0-R risk limits, or production alpha.

## Fail-closed conditions
1. Always fetch the connected Fugle quote for the requested symbol first.
2. Validate symbol, source, quote time, exchange-local market session and `isClose`; do not label a completed-session quote as intraday live.
3. Do not replace missing live data with public web or prior session price.
4. `lastPrice` and five-level book are observations, not standalone entry/exit triggers.
5. Only the existing governed P0-C and P0-R logic may generate executable entry, max-acceptable, stop, sizing, or scores. If not run or missing, display `—` and `觀察` / `禁止交易` as appropriate.
6. Preserve ten-column mobile table in `docs/SKY_MOBILE_RESULT_TABLE_V1_0.md`; sorting by bull score is permitted only for actual governed scores.
7. No automated order placement.

## Follow-on gates (not yet completed)
- Validate authorized standalone Fugle REST/WebSocket access from the Sky runtime, secret management, response schemas, quota and market-data redistribution rules.
- Add a provider adapter with timestamp/session validation, mocked tests and integration telemetry.
- Run paper/shadow data-quality and latency checks before production configuration changes.
