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
- `Sky 波段現在掃一次`
- `Sky 波段快掃`
- `Sky Swing V1.1｜現在掃一次`

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
