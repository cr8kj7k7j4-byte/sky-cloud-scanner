# W7 → W5 Candidate Brief — Overnight-to-Open Reversal

## A. Identification
- Candidate 名稱：Overnight-to-First-30m Reversal for Taiwan
- 提出日期：2026-10-25
- 研究類型：Intraday / Market-state / Timing
- 來源：Iwanaga & Sakemoto (2026), SSRN

## B. Core hypothesis
1. Hypothesis：高幅度隔夜報酬可能對開盤後前 30 分鐘報酬具有反向預測力，且效果可能依波動 regime 改變。
2. 要解決的問題：補足 Sky 對「隔夜資訊如何在開盤被重新定價」的結構性判斷。
3. 市場：先台灣 TWSE/TPEx；必要時以台指 ETF / 台指期作市場層驗證。
4. Horizon：overnight → first 5/15/30 minutes；不直接延伸成全天方向策略。
5. Target / Label：開盤後 5/15/30 分鐘 market/stock residual return。
6. 經濟／市場機制：隔夜資訊與集合競價價格可能過度反應；連續交易恢復後由流動性與價格發現修正。

## C. Data
7. Data source：TWSE/TPEx/Fugle canonical intraday PIT replay data.
8. Feature：overnight return, opening auction/open price, prior-day close, first-bar liquidity/volume, market/sector benchmark.
9. Point-in-Time 可得性：理論上 PASS，須由 W3/W5 確認 canonical replay 欄位。
10. 歷史覆蓋：依現有 canonical intraday dataset 實際 coverage。
11. 缺失值政策：missing open/close or halted symbols fail closed.
12. Corporate action / symbol continuity：必須用 canonical adjustment / symbol contract。
13. Survivorship universe：2023+ PIT universe。

## D. Decision / Execution
14. Trigger / Ranking：先作 conditional evidence test，不預設交易 trigger。
15. Entry timestamp：不得早於必要開盤觀測完成時間。
16. Exit / Holding rule：5/15/30m pre-registered labels。
17. Stop / Target：研究第一階段不做 stop/target tuning。
18. Execution assumption：next observable trade/quote after signal timestamp。
19. Cost assumption：0.45% primary / 0.65% stress round-trip。
20. Liquidity / capacity assumption：沿用 W2 canonical liquidity gates。

## E. Risk
21. 主要風險：集合競價與連續交易制度差異、價格限制、事件日、開盤延遲。
22. Leakage 風險：使用完整 first-30m feature 卻回填較早 entry；禁止。
23. Regime 風險：效果可能集中高波動期。
24. Concentration 風險：極端 gap 樣本可能集中少數股票/事件。
25. Turnover / cost sensitivity：高，必須 after-cost。

## F. Structural difference
26. 與 Production 差異：Production 尚無 overnight→opening-repricing target。
27. 與既有 Research Candidate 差異：不是 fixed-time ranking，也不是 breakout。
28. 與 rejected / frozen family 差異：新 target + 新 causal timing architecture。
29. 是否只是 threshold / period / Top-N / weight / stop-target 微調：NO。
30. 結構差異：overnight information state → opening repricing residual target。

## G. Feasibility gate
- PIT 可驗證：UNKNOWN（預期可行，待 canonical replay audit）
- 可做 untouched OOS：PASS（需保留未使用 future period）
- 可做 after-cost test：PASS
- 可做 portfolio / capacity test：PASS
- 可解釋：HIGH
- 預估複雜度：LOW-MEDIUM

## W7 recommendation
- 新資訊增益：HIGH
- 與 Sky 重複度：LOW
- 值得測嗎：YES
- 送哪個視窗：W5 → W2
- Status：SEND_TO_W5
