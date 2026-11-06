# Sky 有限候選研究備援（2026-11-06）

**獨立於 Production v1.4、Swing V1.0；不是全市場即時 Top100，也不是買進訊號。**

## 可查核的實跑
- GitHub Run: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42156575868
- 2026-11-06 11:27 Asia/Taipei，前一收盤日 2026-11-05。
- 從 TWSE 上市 + TPEx 上櫃每日收盤資料依前日成交金額挑 12 檔，上市、上櫃各預留名額；Fugle 單股即時驗證 12/12 合格。
- CI 12 個針對本流程的測試通過；Artifact ID 13474317765。
- 此處的 12/12 僅代表**被選中的十二檔**報價時效檢查合格，不代表所有約 1,983 檔全市場即時行情覆蓋率恢復，也不代表正期望或真實成交。

## 單一日排程及資料權限
- `.github/workflows/sky-limited-candidate-research.yml` 設台灣交易日每週一至五 **09:20**（UTC 01:20）排程，並保留手動觸發；GitHub Runner 可能晚於 09:20 啟動，須以真實 schedule 日誌驗收。
- 先檢查 TWSE 官方交易日曆（`source_status=PASS` 且 `should_scan=true` 才蒐集），證交所休市／來源失效不得冒充交易日掃描。
- 官方 TWSE `STOCK_DAY_ALL` 與 TPEx `tpex_mainboard_daily_close_quotes` 必須各有可核實、相同且早於執行日的收盤日期，任一市場缺值、不同日、雲端被拒或資料不足即失敗且保留診斷。
- 僅四碼普通股、前收低於 100 元，以前日成交金額**觀察流動性**，不是 Direction/Alpha Ranking；單次最多 20 檔，預設 12 檔，分配兩個交易所名額。
- 使用 GitHub 原有 `FUGLE_API_KEY` 的 `/intraday/quote/{symbol}`，要求當日實際成交最新價及 120 秒時效、現股當沖資格、非處置等條件；不能以昨收、試撮價、委買賣價作已成交價。
- 報告路徑 `output/limited_candidates/latest.json`，Artifact `limited-candidate-research-RUN_ID`，保留 30 天；全天候不下單、不產生交易觸發／最高接受價／停損或 RR。

## 阻擋／下一階段
- 正式當沖全市場 Run #42147456080 目前仍 113/1,983 = 5.70% 有效最新成交價，Fugle TSE/OTC bulk snapshot 權限 `PLAN_BLOCKED`，故正式 v1.4 維持 `BLOCKED_EXTERNAL_DATA_NO_TRADE`。
- 玉山證券行情 API 為**待取得帳戶及使用者授權的可行供應商候選**；不可推定已有金鑰或有全市場串流權限，也不得為取得權限進行真實交易。
- 新排程需等待一次真正 GitHub `event=schedule` 事件，查核 09:20 UTC 換算、延遲、官方交易日期、上市/上櫃名額、Fugle 單股有效率、失敗 Artifact；手動/Push 事件成功不等於定時成功。
- 若要使用本研究結果進入策略證據：先由 W0/P0-G 另行審查規則、樣本偏誤、成本與成交證據。不得回填成過往正式 Sky 訊號。
