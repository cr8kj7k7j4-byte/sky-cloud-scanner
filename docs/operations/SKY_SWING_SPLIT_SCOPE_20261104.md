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
