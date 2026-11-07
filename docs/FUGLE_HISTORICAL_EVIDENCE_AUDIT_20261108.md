# 富果 Developer API：近一年行情資料及回溯可用性驗收（2026-11-08）

**研究專用；不改動 Production，不建立交易訊號或自動下單。**

## 使用的實際授權
官方開發者 REST API：`https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/{symbol}`，以 GitHub Secrets `FUGLE_API_KEY` 的 `X-API-KEY` header 驗證，絕不印出憑證。官方說明每次查詢區間須小於1年，分K自2023-05-23可查，日K支援 `adjusted=true`。本次使用 2025-11-10～2026-11-06（小於1年）。

**請勿混淆**：ChatGPT 富果股票內容插件的重大訊息、營收、融資等資料類型，不等同開發者行情 REST 的端點、授權或精確公告時間。本次資料驗收以 GitHub Runner 實際 API 為準，不以「曾付費」推定每個權限都開通。

## 本次唯讀驗收
- 0050、1101、2330、8088 四標的近一年**未還原日K**與**還原日K**：價格/量格式、日期、異常值、資料列、還原旗標、校正差異。
- 對照同日期 FinMind TaiwanStockPrice 未還原日收盤價，核對共同交易日筆數與最大相對差異；來源差異需明確列出，不能無視。
- 1101、8088 在 2026-11-06 的歷史5分鐘K：檢查時間含時區、成交量及筆數。
- 即使日K與5m可用，仍**不能推導逐筆主動買單/賣壓耗盡**，不能重建券商整戶融資維持率，不可臆定歷史公司公告 `published_at`。
- 沒有原始財報與月營收歷史逐公司公告時間，Revenue MoM 5D/財報事件策略不能通過 PIT Gate 0；也無法僅用日K宣稱 MCR 完整回測成功。
- GitHub artifact 短期保留，不代表已完成長期可審計來源保存；本次不新建排程。

## 回溯驗證／治理
本次完成的是**回溯資料品質與跨供應商一致性檢查**，並不是策略正期望回測。後續應將既有凍結策略的 PIT 事件清單與富果價格對接，標記訊號當時公告是否已經可得，按照次一交易日合理可成交價計價、同時採用0.45%及0.65%成本壓力、完整停損停利、組合容量、真正的樣本外與前瞻再給結論。

Gate：研究狀態 `INSUFFICIENT_DATA`，`production_signal=false`。無合格資訊則不交易。

官方參考：
- https://developer.fugle.tw/docs/data/http-api/historical/candles/
- https://developer.fugle.tw/docs/data/http-api/getting-started/
