# Sky 即時行情全系統資料契約與指令對照（2026-11-04）

Owner: W0 coordination / W3A data / W3B engineering.
Status: DATA_CONTRACT_INTEGRATION; NOT A LIVE-UNIVERSE SOURCE CERTIFICATION.
Production Alpha/Risk changed: NO.
Auto-order enabled: NO.

## Verified external blocker

- Official TWSE+TPEx universe: 1,985 stocks.
- Intraday MIS executed last-trade coverage on 2026-11-04: 90/1,985 = **4.53%**. MIS quote fields often have z='-'; O/H/L/V and reference prices are not executed last prices.
- The existing GitHub Fugle REST key's TSE/OTC bulk snapshot requests returned HTTP 403. ChatGPT-connected Fugle tools and the GitHub key have **separate entitlements**; do not infer that connector access grants Actions credentials.
- A separate daily cross-sectional scan from 2026-11-03 had 1,959/1,985 = 98.69% official EOD coverage. It is **not** a live-market quote coverage statistic.
- At 2026-11-04 10:17, the split-scope research experiment validated 8/8 *shortlisted* Fugle quotes. It is not a full-market price feed.

## Source-and-scope classifications (do not mix)

| Class | Can support | Must not claim |
| --- | --- | --- |
| WHOLE_MARKET_REALTIME_CERTIFIED | Exchange-verified current-session executed prices, explicitly complete coverage | Without fresh TSE and TPEx source, none |
| WHOLE_MARKET_REALTIME_OPERATIONAL | Full executed-quote scope with explicit validated provenance, timestamp and exchange coverage | TPEx official if using MIS OTC |
| CANDIDATES_ONLY_REALTIME | Verified current-day last-trade price and execution timestamp for individual stocks | Full-market market breadth from live prices |
| OFFICIAL_DAILY_CROSS_SECTION | Official prior-day close, volume, price rankings for research | Current-day live price or intraday trigger |
| HISTORICAL_PIT | Proper historical/backtest research | Live execution price |
| BLOCKED_OR_UNVERIFIED | Log, monitor, notify and abstain | Score, A+ buy entry, stop/target derived from a stale price |

All live-mode outputs must record source, timestamp, universe count, TWSE/TPEx coverage, scope, age and unavailable reason. Empty values are NOT zero-price observations. No lastPrice = no current executed price. Do not use closePrice, prior close, bid/ask or OHLCV as synthetic last trade.

## Command-to-data mapping

| Sky command family | Source contract | Current operational state |
| --- | --- | --- |
| Sky 快掃 / Sky 當沖現在掃一次 / Sky v1.4 Dynamic Capital Rotation 掃一下 | Official PIT-active universe + full current-session TSE/OTC executed quotes + Fugle deep-dive | BLOCKED_EXTERNAL_DATA for full market |
| Sky 全市場掃描 / Sky 全市場即時行情 | Combined market proof; do not merge daily scope or candidate quote scope as if full-market current | BLOCKED_EXTERNAL_DATA |
| Sky 波段快掃 / Sky Swing 5D 快掃 | Full current market if actually available, or explicitly separate EOD + candidates research | No full live certification; split scope research only |
| Sky 波段現在掃一次 / Sky Swing V1.1｜現在掃一次 | Frozen canonical D-close whole-market signal + current-day verified candidate executions only | Challenger / not Production; live whole-market certification false |
| Sky 波段更新 <symbol> / Sky 當沖更新 <symbol> / Sky 完整分析 <symbol> | Individually verified Fugle lastTrade and date/time; require position-specific data when needed | Candidate-only realtime if fresh, no automatic A+ |
| Sky 持倉監控 / Sky 警戒 / Sky 持倉更新 | Verify each monitored stock individually; risk, cost, stop from actual positions and governed rules | Partial if any stock quote or position unverified |
| Sky 當沖空方研究 掃一下 | Dedicated independent bearish structure, shorting eligibility, borrow and execution cost plus real market evidence | RESEARCH_ONLY; standalone real-time entry not certified |
| 融資斷頭反彈等資金／籌碼策略 | PIT margin records and separate actual trade trigger data | Research only; historical margin is not current stock price |
| Sky 回測目前模型 / Sky 驗證正期望策略 / Sky 全模型驗證 | historical PIT, W4 forward observations, W6 fill evidence, governance artifacts | Do not replace PIT with realtime |
| 全球盤前掃描 | US/global cross-market timestamped data, separate from TWSE stock executed quotes | Independent time-zone and session validation |

## V1 data safety fixes

1. `src/realtime_quote_evidence.py` is the common executed-trade and source-scope guard.
2. `src/official.py` preserves original MIS trade date without changing the last-price extraction rule.
3. V1.1 reports `operational_full_market_scan=false`, `daily_cross_section_operational` separately, and candidate-only quote coverage.
4. The unified all-market report will reject full-live status without an explicit executed-live scope and certified coverage.
5. Single-stock, Swing and split-scope research never promote a close/reference price to a recent execution.
6. W2 short strategies and research-only challengers do not become Production by connecting a data source.

## Requirements to remove BLOCKED_EXTERNAL_DATA

1. A compliant licensed or authorized and actually reachable TWSE+TPEx current-session executed quote feed for the GitHub Action runtime; quote date, time, last traded price and volume must be auditable.
2. Per-exchange and combined completeness, max quote age and stale/future mismatch checks; both exchanges must independently pass.
3. Re-run a full eligible trading-day scan and independently inspect executed quote count, timestamps, rejection logs, artifacts, and notification delivery. Daily EOD success cannot substitute.
4. Observe additional scheduled scans on actual trading days, with repeatability; manual dispatch success alone does not prove cron scheduling.
5. W4 >=200 truly evaluable forward trade outcomes, >=20 actual trading days, >=2 market regimes, outcome completeness >=95%, single-stock share <=20%, W6 fill/slippage evidence, after-cost PF and expectancy, then W0/P0-G review. None of these are satisfied merely by better prices.

## CI and deployment boundary

The change set is **data contract / observation only**. It changes no production trade setup, entry price, stop, target, capital/risk, or automatic orders. Existing schedules stay in GitHub Actions. After CI, merge to main only as data safety changes, and verify actual post-merge run; never claim an unverified whole-market source has been repaired.
