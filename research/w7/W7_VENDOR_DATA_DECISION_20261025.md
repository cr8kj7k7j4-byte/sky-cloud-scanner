# W7 Vendor / Data Decision — 2026-10-25

> External intelligence only. No Production change.

## 1. Fugle — TRIAL_FIRST

### Observable facts
- Stock historical candles support 1/3/5/10/15/30/60-minute bars and daily/weekly/monthly.
- Stock minute bars are available from 2023-05-23.
- Stock daily bars: listed/OTC back to 2010; index back to 2015.
- Futures historical candles support minute bars, regular/after-hours sessions, and continuous contract aliases.
- Futures minute bars are available from 2017-06.
- Futures daily/weekly/monthly are available back to 2010.
- Current plans: Developer 300 websocket subscriptions / 2 connections, Advanced 2000 / 2; historical API 60 req/min.

### Sky relevance
- Overnight-to-open reversal can be tested on 2023+ minute stock/index data.
- TXF/ETF/spot lead-lag can be tested with minute futures history and 2023+ minute stock/index history.
- Does not provide historical broker-branch identity flow.

### Decision
TRIAL_FIRST.
Use available/current Fugle capability before purchasing larger capacity. Upgrade only if W5/W2 confirms a structural candidate and actual rate/subscription limits become binding.

## 2. TWSE Broker Branch Daily Report — DO_NOT_BUY NOW

### Observable facts
Official TWSE e-shop full-market buy/sell daily report:
- start date: 2012-10-25
- daily frequency
- fields include security code, broker, transaction price, buy shares, sell shares
- produced after market close
- full-market excluding warrants listed at NT$80,000/month for internal use
- branch/self-trading aggregation caveats apply

### Sky relevance
This can support 1D–5D broker-identity / branch-flow research, not true intraday order identity.
It is structurally novel relative to current Sky volume/RS inputs.

### Risks
- Expensive before evidence of incremental value.
- Daily after-close granularity prevents intraday causal use.
- Broker branch codes / branch lifecycle need PIT mapping.
- Historical skill scores must be computed past-only.
- Report definition aggregates certain proprietary trading into head office.

### Decision
DO_NOT_BUY NOW.
Only revisit after:
1. W5 accepts the hypothesis;
2. a free/sample or narrowly scoped extract confirms schema/branch continuity;
3. a pre-registered 1D–5D target is fixed;
4. expected research value justifies cost.

## 3. TAIFEX official historical transaction/order data — RESEARCH_ONLY / TRIAL_FIRST IF NEEDED

### Observable facts
TAIFEX provides historical datasets including:
- futures trade files
- futures order files including market-maker quotes
- interval disclosure files
- tick-by-tick disclosure files
TAIFEX states recent ~30 trading days of per-trade data are downloadable from its website; older historical data are obtained through its paid E-Data Shop.

### Sky relevance
Potentially valuable for W6 execution/microstructure and for validating minute lead-lag at higher fidelity.

### Decision
Do not purchase yet.
First validate the lead-lag hypothesis using Fugle minute history. If information survives after cost and timestamp causality, then evaluate official tick/order data as a second-stage fidelity upgrade.

## Purchase priority
1. Fugle existing/current plan — USE FIRST.
2. No broker-flow purchase now.
3. No TAIFEX paid tick/order purchase until minute-level evidence survives.
4. No global vendor purchase for Taiwan-core research at this stage.
