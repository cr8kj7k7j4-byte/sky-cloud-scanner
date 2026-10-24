# Sky v1.5 Research Architecture

> Status: **RESEARCH_ONLY**
>
> 本文件定義 Sky 下一版研究架構。任何新增因子、參數、Ranking 或 Market Regime 規則，在完成驗證前不得直接進入正式 Production Scanner。

## 1. Core Pipeline

P0-A Data Engine  
→ P0-B Feature Engine  
→ P0-C Decision Engine  
→ **P0-O Opportunity Ranking Engine**  
→ P0-R Risk & Portfolio Management Engine  
→ **P0-X Execution Engine**  
→ P0-P Position Management  
→ P0-D Learning & Validation Engine  
→ **P0-L Candidate Strategy Lab**

## 2. P0-C vs P0-O

### P0-C: Hard Gates
P0-C 決定「能不能交易」。重大否決條件不可被其他分數抵銷，例如：
- 流動性不足
- 漲停或無合理成交空間
- 價差過大
- P5 / P6 不適合新進場
- Anti-Chase 失敗
- 突破失敗
- Net RR 未達門檻
- P0-R Kill Switch 啟動

### P0-O: Cross-sectional Ranking
P0-O 只處理已通過硬性 Gate 的候選標的，回答：
> 有限資金現在應優先配置在哪一個交易機會？

研究候選特徵：
- intraday_momentum
- market_relative_strength
- sector_relative_strength
- volume_anomaly
- vwap_structure
- breakout_quality
- entry_quality
- net_rr
- anti_chase_risk（penalty）
- liquidity_slippage_risk（penalty）

輸出：
- opportunity_score: 0–100
- opportunity_rank: 1..N

**Opportunity Score 不是實際勝率或上漲機率。**

## 3. P0-L Candidate Strategy Lab

任何新規則只能依下列流程晉級：

Hypothesis
→ Candidate
→ In-Sample
→ Sensitivity Test
→ Walk-Forward
→ Independent OOS
→ Market Regime Test
→ Cost / Slippage Stress
→ Paper Trading
→ Production Review

單次漂亮回測只能形成「模型修正假設」，不能直接升級正式模型。

## 4. Parameter Robustness Protocol

禁止以「單一歷史最佳參數」作為正式設定依據。

每個 Candidate 至少要比較：
- 樣本數
- PF (Profit Factor)
- Expectancy
- MDD
- MFE
- MAE
- R Multiple
- 成本後績效
- 不同 Market Regime 表現
- 鄰近參數穩定性

優先選擇「穩定參數區域」，而不是最高單點。

## 5. Market Regime Candidate

研究版狀態：
- Risk-On
- Neutral
- Risk-Off
- Crisis

用途：
- 調整 A+ 門檻
- 調整 Portfolio Heat
- 調整最大同時持倉數
- 必要時觸發 Kill Switch

此規則在完成正式回測前保持 Candidate，不可直接做 Production 市場狀態定義。

## 6. P0-X Execution Engine

風險報酬不得只使用理論成交價。

Execution-adjusted RR 研究需納入：
- 手續費
- 證交稅
- 滑價
- Bid-Ask Spread
- 流動性
- 成交機率
- 委託失敗 / 錯單保護
- 策略容量

## 7. Validation Priority

優先比較三組：

- A: 現行 Sky
- B: Sky + P0-O Ranking
- C: Sky + P0-O Ranking + Market Regime + P0-R

比較指標：
- Net PF
- Net Expectancy
- MDD
- MFE
- MAE
- R Multiple
- Sample Size
- Regime Split
- Parameter Stability

只有在 B/C 對 A 的改善能通過樣本外、成本壓力與穩健性測試後，才可討論升級 Production。

## 8. Research Principle

框架穩健性 > 單一最佳參數。

AI 的工作是提出假設、寫程式、跑資料、回測、找失敗原因與產生下一個 Candidate；
AI 不得憑語言生成宣稱不存在的績效、勝率、即時價格或回測結果。
