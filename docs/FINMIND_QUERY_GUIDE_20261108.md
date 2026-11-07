# Sky FinMind 股票資料查詢（唯讀研究）

## 入口與證據

- Workflow: `.github/workflows/finmind-research-query.yml`
- 程式: `research/finmind_query.py`
- 驗收 Run: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42409566510
- 範例：2330，2026-10-01 至 2026-11-06，股價 24 列、融資融券 24 列、法人分項 120 列，三種資料集均通過基本 API 與日期檢查。
- JSON: `research_output/finmind_query_result.json`（Actions artifact `finmind-research-query`）；僅最新日期的最多 12 列資料、欄位名與筆數，避免過度輸出。

## 查詢方式
- 預設僅 push 測試分支 `integration/finmind-api-acceptance-20261108` 時執行一次，與正式模型獨立。
- 後續主分支正式啟用之前，應審核 PR #306；`workflow_dispatch` 自訂輸入在工作流程可見且可手動執行時使用。
- `symbol`: 4–6 位數字代碼；`start_date`、`end_date`：YYYY-MM-DD；最大查詢範圍 366 天。
- 讀取 `FINMIND_TOKEN` GitHub Actions Secret；切勿提交、列印、傳送 Token。
- 只讀取 `TaiwanStockPrice`、`TaiwanStockMarginPurchaseShortSale`、`TaiwanStockInstitutionalInvestorsBuySell`，不下單，不新增排程。

## 限制
- PASS 表示指定股票、期間、資料集回傳非空且日期格式符合；不代表全市場涵蓋率、盤中即時、PIT 完整性、資料絕對準確或策略獲利。
- 融資融券欄位不直接等於融資維持率；法人各分項不可將單一欄位誤作總買賣超。
- 無法從 ChatGPT 的 GitHub 連接器任意呼叫 API 或直接讀取 GitHub Secret；目前依 GitHub Actions 啟動與讀取日誌、Artifact 的方式完成查詢。
- 須進一步驗證官方單位、調整、每個交易日覆蓋率、與 TWSE/TPEx/Fugle 一致性。
- Production 不變，狀態維持 RESEARCH_ONLY。
