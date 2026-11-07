# Paid Fugle primary live market contract (2026-11-08)

Status: PROPOSED / requires API-entitlement and runtime acceptance before Production merge.

## Scope
- Sky Day Trading v1.4 whole-market scanner (`src/main.py`): Fugle TSE/OTC snapshot is **screening-only**. Until true per-symbol executed-trade coverage can be verified, trading decisions remain blocked.
- Sky swing candidate/5D runner (`src/swing_live_scanner.py`): Fugle bulk is a research candidate screen; candidates are independently checked using Fugle individual lastTrade.
- Sky Swing V1.1 intraday execution overlay (`src/swing_v11_live_scanner.py`): verified per-symbol Fugle quote only; D-close frozen signals remain unchanged.
- `src/sky_single_stock_realtime.py`: already requires Fugle per-symbol current-session trade evidence.
- Historical backtests: point-in-time historical data, not live snapshot replay.

## Mandatory fail-closed criteria
1. Repository/cloud runtime `FUGLE_API_KEY` is present and authorized for the actual REST endpoint. A ChatGPT Fugle connector entitlement does not prove cloud REST entitlement.
2. Snapshot offers `lastPrice` (which can include trial) and `lastUpdated` (snapshot time), **not an individual lastTrade timestamp**. Use snapshot date, freshness, nontrial last price and volume for screening only. `closePrice`, download time and MIS cannot certify an actual execution. Individual candidate `/intraday/quote/{symbol}` must pass verified `lastTrade.time` before even considering trade eligibility.
3. Screening coverage meets existing 80% overall / 70% each exchange constraints using fresh snapshot quotes. This does **not** prove market-wide executed-trade coverage. New trade decisions remain blocked until independent executed-price provenance and strategy/risk gates pass.
4. Candidate per-stock quotes must pass freshness validation and all separate risk/strategy gates.
5. Sunday/holidays and pre/post-market runs do not magically become live trade evidence; fail closed and show timestamps.
6. No automatic orders, no strategic promotion and no historical model retuning.

## Release gates
- Confirm paid REST key entitlement for `/snapshot/quotes/TSE`, `/snapshot/quotes/OTC` and `/intraday/quote/{symbol}` in the actual GitHub/cloud environment.
- Run unit tests and explicit negative tests for 403, no snapshot update time, stale date, missing last price, and partial exchange coverage. Run separate individual-quote lastTrade proof tests.
- Manually execute each affected workflow on an **open trading day**, check artifacts, quote coverage, API call quotas, nonempty source provenance, and UI date/time.
- Confirm GitHub scheduled execution and deployed Cloud Run **revision** separately.
- Do not merge/deploy until W0/P0-G approval and acceptance evidence are recorded.

Previous `docs/SKY_REALTIME_COMMAND_CONTRACT_V1_0.md` reflects the earlier MIS-primary runtime. This document proposes a replacement for the affected entrypoints only; remaining commands and dashboard endpoints need separate inventory.
