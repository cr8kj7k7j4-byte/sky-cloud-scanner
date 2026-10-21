# Sky Cloud Scanner v0.3｜官方母池＋盤中備援版

## 本版修正重點
v0.2 的母池其實先依賴 Fugle ticker list，與「TWSE 官方→TPEx 官方→合併→Top100→Fugle 深查」的固定順序不完全一致。v0.3 已改成：

1. TWSE 官方 OpenAPI 建立上市普通股母池。
2. TPEx 官方 OpenAPI 建立上櫃普通股母池。
3. TWSE MIS 批次取得盤中報價；上市視為 TWSE 官方盤中來源。
4. OTC 在 MIS 可取得盤中報價時，可作「操作備援」；但它不是 TPEx 官方盤中全市場來源。
5. 因此 `STRICT_OFFICIAL_MODE=1` 時，只要 TPEx 官方盤中全市場資料無法驗證，報告一定顯示「未完成全市場掃描」，候選最高只能 A，絕不冒充 A+。
6. Fugle 只負責優先候選的 ticker/quote/5分K 深查；若帳號方案支援 Snapshot API，也可在主資料失效時當備援，但仍會標示來源降級。

## 為什麼要這樣設計
TPEx 公開 OpenAPI 的 `tpex_mainboard_quotes` 是官方且免費，但屬日頻/收盤後更新用途，不應冒充完整盤中即時全市場來源。TPEx 的交易看板有「即時行情／漲跌排行／成交排行」，但免費對外可穩定自動化的完整盤中 API 未在本版驗證完成；TPEx 另有正式即時資訊商品。因此嚴格模式寧可 Fail，也不虛構完整 Top100。

## GitHub Secrets
Repository → Settings → Secrets and variables → Actions → New repository secret

必填：
- `FUGLE_API_KEY`

選填：
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 第一次測試
Actions → `Sky Cloud Scanner v0.3` → Run workflow。

依序確認：
- Diagnose data sources
- Run scanner
- Upload scan report

Artifact 會包含：
- `output/latest.txt`
- `output/latest.json`
- `source-diagnostics.json`

## 排程（Asia/Taipei）
- 09:10
- 10:10
- 11:10
- 12:10
- 13:00

GitHub Actions 目前官方支援 `timezone: Asia/Taipei`。

## 分類邊界
- `rank_score` 只做候選排序，不是勝率、SSS 或 EES。
- 未完成全市場掃描 → 最高只能 A。
- A+ 必須：即時資料充分、Trigger 已確認，而且 Market Gate → Sector/RS → Multi-Timeframe → SSS → Phase → Anti-Chase → Breakout Quality → Setup+Trigger → Devil's Advocate → EES → RR Gate 全部通過。
