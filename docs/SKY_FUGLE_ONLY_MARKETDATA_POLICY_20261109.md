# SKY｜富果付費行情唯一來源政策（2026-11-09）

## 使用者要求
所有 Sky 指令與當沖、波段、隔日、融資研究、六模型、手機/ChatGPT 顯示的**市場報價／K 線／成交量／成交時間／量價特徵**一律使用已授權的 Fugle Developer 付費資料。不得在 Fugle 不足時自動改抓 TWSE MIS 或其他免費行情並冒充同一資料品質。

## 目前執行層
- `SKY_FUGLE_ONLY_MARKETDATA=1` 為 Python 行情路由預設；`scan.yml` 也明確設 1。正式行情路由不得以設定值關閉此來源限制；若程式仍保留非富果價格備援分支，必須列為待修復。
- `src.quote_provider.collect_market_quotes` 富果資料不達最新成交門檻時，保留來源與缺值、NO_TRADE，不請求免費 MIS 備援。
- `src.diagnose_sources` 停止免費 MIS 診斷抽樣，只查 Fugle 個股／TSE/OTC bulk。
- `src.official.fetch_mis_quotes` 有中央防線，富果專用模式阻止免費 MIS 請求。
- `src.fugle` 提供真實 API 用戶已購買的市場資料；不新增付費服務或暴露密鑰。
- 既有 `research.sky_full_universe_information` 已直接使用 Fugle bulk，對缺失或未驗證成交時間的觀察只列研究資料。

## 官方非行情例外
TWSE/TPEx 官方股票代碼母池、上市上櫃身分、交易日曆與法規制度可作**識別、資料完整率分母、合規驗證**；不得把它們的免費價量當成研究／交易行情來源。GitHub 的研究證據、模型版本與 Workflow 不是行情來源。

## 尚未完成的全系統驗收
這次中央路由與主掃描切換不等於已逐一認證所有其他 repo、研究腳本、外部 App/Cloud Run 或歷史資料來源。需逐個檢查：資料源是否真為 Fugle、API 權限與配額、日期時間、欄位 schema、必要價量特徵、完整 13 欄結果及來源時間。若 Fugle 沒有該指標或權限不足，列 `待確認` 或 `DATA_BLOCKED`，不得私自替代或補造。

## 風控
任何行情或模型尚未驗證，不得自動下單、不放寬 P0-R、不得用延遲收盤價冒充盤中成交，也不得以未驗證研究評分當作勝率。這是資料來源政策，不是策略升版。
