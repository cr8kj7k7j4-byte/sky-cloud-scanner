# Sky W0／P0-G 研究級驗收審查送件（未核准）

日期：2026-11-11（台灣時間）  
治理狀態：**HOLD / INSUFFICIENT_DATA / NO_TRADE**  
適用：Sky v1.4 Dynamic Capital Rotation；此文件只彙整可讀取證據，不是 W0／P0-G 核准。

## 多視窗責任與去重

| 範圍 | 唯一主責 | 重疊規則 |
| --- | --- | --- |
| 三市場 Snapshot／候選 Quote | #511 | 不再新建重複行情掃描器；#510 只核對差異 |
| 五分鐘 K 因果性 | #512 | 沿用原有修補與 offline tests，不用其他 PR 替代真實驗收 |
| 成本後 RR／PAPER_ONLY | #508 | 不能用假造模擬成交替代來源完整的帳本 |
| 跨 Workflow 付費 API 入口／去重 | #515 | 動作必須有共用互斥與請求紀錄證據；本次只完成唯讀結構盤點 |
| 事件修復控制器安全 | #520 | #518 額外提案不得擅自併入 main；核對事件來源 SHA 和獨立審核 |

## 逐 Gate 來源與證據

1. **Snapshot 代碼覆蓋 Gate（研究）**：Fugle TSE+TIB/OTC 真實 Run [#42863180723](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42863180723)，2026-11-11 01:16 TPE 讀取 2026-11-10 行情，TWSE 1091/1091、TPEx 895/895；Artifact `sky-snapshot-integrity-42863180723`。只證明股票代碼參考覆蓋，**不是最新逐股成交時間**。
2. **Quote 實際成交時間 Gate（研究樣本）**：Run [#42761552290](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42761552290)，2026-11-10 13:21 TPE，12/12 候選個股 Quote 顯示 `FRESH_EXECUTED_TRADE`、0 HTTP429；Artifact `sky-chat-42761552290`。**不是 #512 最新 SHA 的真實盤中驗收，也不是全市場逐筆時間認證**。
3. **五分鐘 K 因果 Gate**：上述舊 Run 曾記錄 2409/TWSE、5202/TPEx 各 53 根 5m；#512 head `9ce0df9ffdff460167e0537e51c15f12a0ac5946`，Run [#42869603431](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42869603431) 76 個離線測試 PASS，含 13:21 排除 13:20～13:25 形成棒。**仍缺該 head 的真實盤中 raw Quote/Ticker/Candles、同 SHA Artifact、回讀及獨立審核**。
4. **執行成本／PAPER_ONLY Gate**：PR #508 head `aa379bbc5061a08aba099dcfef64ac6d994e6938` 19 項 CI PASS，毛 RR=1.5 但費後 RR<1.5 禁止進場，執行成本缺值禁止買進，不改目標／放寬停損。Run [#42863564893](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42863564893) PAPER_ONLY offline tests + Artifact 通過，但 `paper_performance_verdict=INSUFFICIENT_DATA`，缺獨立可核的訊號／市場時間／入出場／填單假設／實際估計成本帳本；不可聲稱完成績效或實盤成交。
5. **付費 API 去重 Gate**：PR #515 靜態列出不同手動／推送觸發與 concurrency groups；**尚無跨 Workflow 共用 runtime lease、provider request ID/呼叫量帳本、同時觸發防護的真實證據**。停用 GitHub `schedule` 不等於排除手動重複付費；沒有證據不得宣稱實際重複扣款。W0 稽核僅讀 GitHub 不呼叫 Fugle。
6. **自動修補閉環 Gate**：既有主控制器 `sky-governed-auto-repair.yml` 事件觸發已測試；#520 事件來源 SHA/重試防護仍是 Draft，未獲獨立審核，亦缺真實失敗 CI → Draft 修補 PR → 下游 CI／Artifact 全鏈閉環。#518 須與 #520 去重，不重建第三套。
7. **正式 W0／P0-G**：上述 Gate 未全通過，`PROMOTE`、`PRODUCTION_ELIGIBLE` 均 **否**；審查結果 **HOLD／INSUFFICIENT_DATA**。此文件不是獨立簽核，須獨立審查人員實際核對最新 SHA、來源 Artifact、成本、風控及治理登錄。

## 後續最小可驗收順序

- 先等待有效交易時段，核對其他視窗未執行同一付費 probe，使用 #512 最新 SHA 限額唯讀讀取上市／上櫃候選 Quote、Ticker、5m 原始資料，證明 K 棒起始／完成時間與未完成棒排除，留存 Artifact。同一 SHA／同一交易日，不能用歷史 Runner 替代。
- 優先補跨 Workflow 共用「付費 API 執行鎖／唯一 request receipt」及失敗釋放證據，先在研究分支 offline 測試，不恢復 GitHub cron。
- PAPER_ONLY 需使用實際掃描的訊號識別碼及資料時間，按可追溯成本估算生成模擬帳本，再驗證時間因果、單筆風控、費後 RR、現金部位限制；不得創造填單、臆造獲利。
- 最後由獨立 W0／P0-G 治理審核，若任何 Gate 尚未核實，保持 HOLD/NO_TRADE。

**硬性限制：** 不自動下單；不調高目標、不放寬停損；不自行合併 Production；GitHub 定時 schedule 維持全部暫停，既有 ChatGPT 每小時任務獨立複核。
