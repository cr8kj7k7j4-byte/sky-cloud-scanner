# W7 → W5 Candidate Brief — Taiwan Dynamic Futures/ETF/Spot Lead-Lag

## A. Identification
- Candidate 名稱：Taiwan Dynamic Futures/ETF/Spot Lead-Lag State
- 提出日期：2026-10-25
- 研究類型：Intraday / Cross-market / Market Intelligence
- 來源：Taiwan futures/spot academic evidence; 2026 Asian cross-listed index futures evidence.

## B. Core hypothesis
1. Hypothesis：台指期、ETF 與現貨資訊吸收速度在不同流動性/波動狀態下不一致，數分鐘級 lead-lag 可作為市場狀態/confirmation input。
2. 要解決的問題：補足 Sky Market→Sector→Stock 流程中「上游市場是否已先反映資訊」。
3. 市場：TX futures / Taiwan index ETFs / TAIEX / constituent basket.
4. Horizon：1–5 minute dynamic lead-lag state；不預設單一固定 lag。
5. Target / Label：future spot/index residual movement conditional on futures/ETF innovation.
6. 機制：price discovery、leverage、liquidity、informed trading、cross-market arbitrage。

## C. Data
7. Data source：TAIFEX/Fugle futures + TWSE/TPEx/Fugle spot/ETF synchronized PIT data.
8. Feature：timestamp-aligned returns, quote/trade imbalance where available, spread/liquidity, volatility state.
9. PIT 可得性：UNKNOWN until synchronized historical contract is audited.
10. 歷史覆蓋：Fugle futures minute history available from 2017-06; canonical research window should remain governance-controlled.
11. Missing policy：cross-market timestamp gaps fail closed.
12. Corporate action：ETF/stock adjustment per canonical rules.
13. Survivorship：PIT universe for constituent tests.

## D. Decision / Execution
14. Trigger / Ranking：first stage produces lead/lag state feature, not direct trade.
15. Entry timestamp：strictly after source-market innovation is observable.
16. Exit / Holding：1/3/5m label grid pre-registered.
17. Stop / Target：none in feature-validation stage.
18. Execution：timestamp causality mandatory.
19. Cost：0.45% / 0.65% if converted to tradable strategy; feature stage also reports gross information coefficient.
20. Liquidity/capacity：index/futures capacity differs from small-cap stocks; downstream application must revalidate.

## E. Risk
21. Main risks：clock synchronization, stale index print, asynchronous markets, derivative roll, auction periods.
22. Leakage：using future spot constituent updates inside source signal.
23. Regime：lead direction can reverse.
24. Concentration：large-cap index constituents.
25. Cost sensitivity：very high if converted into minute-level trading.

## F. Structural difference
26. Production difference：new cross-market data family / timing architecture.
27. Existing research difference：not fixed-time stock ranking.
28. Frozen-family difference：new PIT data family and cross-market lead-lag target.
29. Local retune only：NO.
30. Structural novelty：cross-market synchronized PIT information-state feature.

## G. Feasibility
- PIT：UNKNOWN
- untouched OOS：PASS if future period reserved
- after-cost：PASS
- portfolio/capacity：PASS
- explainability：HIGH
- complexity：MEDIUM-HIGH

## W7 recommendation
- 新資訊增益：HIGH
- 與 Sky 重複度：LOW-MEDIUM
- 值得測嗎：YES
- 送哪個視窗：W5 → W2（資料同步可能需 W3）
- Status：SEND_TO_W5
