# W7 Evidence Dossier — Taiwan Futures / ETF / Spot Dynamic Lead-Lag

## Name
Dynamic Cross-Market Lead-Lag / Price Discovery State

## Type
Intraday cross-market / market intelligence

## Sources
- Lee, Wu & Yang (2013): Taiwan futures returns significantly lead spot returns; foreign institutional futures trading showed predictive information.
- Chen et al. (2021): regular Taiwan index futures contributed more price discovery than mini futures; institutional arbitrage and margin-system changes altered relative price discovery.
- Older Taiwan evidence is mixed: some studies found spot dominance or bidirectional causality, reinforcing that leadership is state-dependent rather than fixed.

## Market
Taiwan index futures / spot / ETF.

## Core method
Do not assume "futures always lead."
Estimate a PIT-observable dynamic market state using synchronized 1–5m returns/liquidity, then test whether futures/ETF innovations improve next-minute spot/index residual forecasts.

## Empirical strength
MEDIUM-HIGH as a market-structure phenomenon, but direction and magnitude are regime/time dependent.

## OOS
Requires new Taiwan pre-registration and untouched OOS.

## Transaction cost
Must pass Sky cost stress if made tradable. It may also be useful as a context/confirmation feature even if not standalone alpha.

## Replicability
HIGH-MEDIUM.
Fugle futures minute history exists from 2017-06; stock/index minute history from 2023-05-23 enables synchronized 2023+ research.

## Sky overlap
LOW-MEDIUM.
Sky has market/relative-strength context but not a synchronized cross-market PIT lead-lag state.

## Data requirement
- TXF/MXF minute data
- TAIEX / ETF minute data
- synchronized timestamps
- roll handling
- day/night session mapping
- optional later tick/order upgrade via TAIFEX

## Estimated integration cost
MEDIUM.

## Main risks
- asynchronous timestamps
- roll jumps
- stale index values
- auction windows
- leadership reversal
- high turnover if naively traded

## Worth buying?
NO paid tick data initially.
Use Fugle minute history first.

## Worth testing?
YES.

## Handoff
W5 → W2; W3 if synchronization contract is missing.

## Status
SEND_TO_W5
