# Sky 富果優先即時行情｜W3B 工程驗收紀錄

日期：2026-11-08 (Asia/Taipei)；對應 PR #323。

## 已實作
- `src/main.py` 透過 `src/quote_provider.py` 優先取得 Fugle TSE/OTC bulk snapshot，嚴格檢查實際成交價格及當日實際成交時間。
- 失敗時獨立執行 TWSE MIS 備援；兩者涵蓋率**不得合併湊門檻**；保留 `fugle_primary_evidence`、`live_market_evidence`、`market_quote_provider`、`market_quote_fallback_used`。
- 保留 P0-R、STRICT_OFFICIAL_MODE，TPEx 官方即時認證仍為 false，無自動下單。
- CI: `test-fugle-primary-provider.yml` 與其他 PR checks；請查 PR 最新一次 SHA 與執行結果，勿沿用舊 SHA 成功紀錄。

## 資料驗收門檻（預先聲明）
1. `FUGLE_API_KEY` 存於 GitHub Secrets；禁止在 log/report 暴露。
2. 交易日 09:05／09:15／09:30／09:50／10:15（台北時間）核對實際 GitHub scheduler 事件時間、Runner 開始時間、報表產生時間；排除假日與重複觸發。
3. TSE 與 OTC 分別查證帳號權限、實際成交時間、有效股票數、失敗代碼；執行價不得以 closePrice、前收、買賣五檔代替。
4. 全市場有效成交涵蓋率 ≥80%，兩個市場各 ≥70%，且母池與資料時間有效；即使達標仍不自動宣稱 TPEx 官方認證或實盤可交易。
5. API 失效、日期不符或單檔驗證失敗，立即 fail-closed；保留可讀的手機報告／告警佐證。
6. Cloud Run 版本 SHA、部署狀態、公開健康檢查及手機實際查詢須另驗收，不得由 GitHub CI 推論。
7. W0/P0-G 的 18 項升版 Gate、前瞻樣本、完整成本後績效與風控，仍然獨立；未通過不得放行交易訊號。

## 目前判定
- **工程修復：PR 待審、非 Production**。
- **富果付費實盤行情授權／涵蓋率：尚待交易日真實驗收**。
- **Cloud Run 部署與手機端：尚未驗收**。
- **策略正期望值／交易允許：未證實／NO_TRADE**。

舊有定時 Workflow 已存在，不新增 ChatGPT 排程，不以 CI 自動通過代表正式上線。
