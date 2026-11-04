# Sky 波段分層行情替代流程｜2026-11-04

## 設計與權限
- **目的**：在 Fugle 整批 snapshot API 403 且 MIS 盤中 `z='-'` 大量缺值時，提供免費且來源可追溯的分層研究流程。
- **橫斷面**：TWSE `STOCK_DAY_ALL` + TPEx `tpex_mainboard_daily_close_quotes`，若 TPEx 主要端點傳輸中斷，使用官方 `tpex_mainboard_quotes` 收盤備援。嚴格以官方來源各筆日期和交易日期一致性判斷，不能混用不同交易日。
- **盤中**：只對前一交易日的研究候選，使用現有 Fugle 單檔即時報價 API，要求與當日一致且有15分鐘以內可核對的成交時間戳記。
- **資料分離**：官方每日收盤市場涵蓋率 ≠ 當日盤中全市場即時報價覆蓋率。後者沒有足夠授權來源，必須永遠是 `null / UNVERIFIED`，不可宣稱達標。
- **治理**：`RESEARCH_ONLY_NOT_PRODUCTION`，所有 candidate `strategy_signal=false`、`production_eligible=false`、`action=等待`。無買點、停損、成本後RR時不准生成交易訊號。
- **OTC**：分層全市場收盤使用 TPEx 官方；其他 TWSE MIS OTC 只能作備援，不能宣稱 TPEx 官方即時。

## 已完成程式
- `src/swing_split_scope_scanner.py`：每日收盤跨市場覆蓋率、日期一致性、研究候選、Fu​gle 單檔查核與時間戳記。
- `.github/workflows/swing-split-scope-research.yml`：交易週一至週五 09:15 Asia/Taipei，保留 JSON Artifact、GitHub Steps Summary、測試與失敗狀態。
- `tests/test_swing_split_scope_scanner.py`：市場與日線來源解析、日期不一致、未收盤當日資料拒絕、報價時間新鮮度。
- `tests/test_official_mis_coverage.py`：既有7項 MIS/Fugle 資料安全測試。

## 已驗證的成功證據
2026-11-04 09:36（台灣）GitHub Actions:
https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41755149811

- 官方日收盤日期：2026-11-03。
- 母池：1,985；官方日收盤有效：1,959；全市場 D-close 98.69%。
- TWSE：99.45%；TPEx：97.76%。
- Fugle 8/8 只驗證日期（時間戳記加強版另行測試，不可拿8/8充作最新成交保證）。
- 當次12項測試通過，Workflow success，Artifact available。
- **此完成僅限「分層資料研究替代流程」，不代表原訂盤中全市場即時行情80%已完成。**

## 尚待驗證／外部阻擋
- 完整盤中全市場即時：2026-11-04 09:25 左右覆蓋率4.53%（90/1,985），Fugle bulk snapshot 403；不可以分層98.69%替代。
- 新增時間戳記檢查後需以最新 Workflow 實跑記錄核對。
- 排程已寫入，**實際 09:15 定時觸發尚待下一個交易日驗證**；手動／push 執行成功不等於 cron 成功。
- 下游正式 Sky Swing V1.0 exact executable rule spec 仍有 W0 governance blocker。
- 不增加資料服務購買、不更改 Production、不自動下單。

## 失敗處置
每日盤後官方來源請求失敗、日期不同、上市上櫃涵蓋不足： fail closed，不沿用舊候選。
富果候選個股缺報價或時間戳記過期：只顯示未驗證，不輸出可買訊號。
GitHub Actions Workflow summary 與 artifacts 為查驗入口。


## 最終重驗證（2026-11-04 09:39～09:40 Asia/Taipei）
- GitHub Run： https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41755405440
- **13/13 單元／安全測試全部通過；全部 Workflow 步驟通過；Artifact 已上傳**。
- 每日收盤資料日期：2026-11-03；全市場日收盤涵蓋 **1,959／1,985（98.69%）**，TWSE **99.45%**、TPEx **97.76%**。
- 候選單檔 Fugle 查核 **8／8**，同日且可驗證的 `lastUpdated` 時間戳記 **8／8**；單檔報價不等於全市場即時覆蓋率。
- 資料來源錯誤 0；`daily_scope_status=PASS_DAILY_CROSS_SECTION`。
- `live_whole_market_coverage_pct=null`，`live_whole_market_certified=false`；原本盤中全市場 ≥80% 目標仍因權限／來源而 BLOCKED。
- 新 workflow 的 GitHub cron 已設定 09:15 Asia/Taipei；**尚待下一個實際交易日排程觸發驗證**。此輪 push 成功不等於定時成功。
- 此項目可作為**資料研究替代流程已完成**，但不得視為全市場即時行情或正式 Production 策略修復結案。


## 2026-11-04 22:48 再驗證（台灣時間；最新證據）
- 核對正式 GitHub Actions Run: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41850865342 ，head SHA `1115ed0d`。
- **19項單元測試通過**，掃描及 Artifact 有實際產出；Workflow 最終 `failure` 是資料日期防護阻擋，非測試失敗。
- 官方股票母池1,985；可解析日收盤1,967（99.09%）；但官方來源仍混合 **2026-11-03 與 2026-11-04**。不能用高覆蓋率掩蓋日期不一致。
- 程式已加入 TPEx 官方備援來源日期對齊重查；本次 `official_tpex_source_used=mainboard_quotes`，`market_data_errors` 記錄 TPEx 主端點 `ConnectionError`。備援依然不能解除跨日不一致，故 `daily_scope_status=BLOCKED_DAILY_CROSS_SECTION`。
- 當次候選即時查核 `0/0`（上游資料失效後不產生新候選），**不能沿用上午舊候選**。
- 正式全市場即時行情 ≥80% 未通過；先前 MIS 盤中 4.53%（90/1,985）與 Fugle snapshot 403 的權限限制仍在。
- 本次已增加備援來源識別及日期對齊測試；**不允許當日 TWSE/TPEx 來源日期不一致時強行通過**。
- 09:15 Asia/Taipei schedule 於當日09:15之後才建置，**2026-11-05 為下一個待驗證交易日**（以官方日曆為準）。本次驗證為 push 事件，並非定時觸發成功證據。
- **結案劃分**：資料路徑、來源追蹤與防護工程完成；11/04 夜間有效日收盤報告 BLOCKED；全市場盤中即時報價與下游 Swing V1.0 正式策略仍未完成。未經 W0 治理審查不得啟用交易。
