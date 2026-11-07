# Sky 月營收／財報事件 PIT 證據驗收｜2026-11-08

**狀態：INSUFFICIENT_DATA。程式能查詢不代表歷史 PIT 資料已驗證。**

## 起因
`SKY_SYSTEM_REGISTRY_V2_1.md` 記載 2023–2026 月營收歷史 87,588 個公司月份的真實 MOPS 申報時間戳驗證數為 **0**。既有 Revenue MoM 5D、Revenue YoY Acceleration 5D 都保持 PRE_PIT_CANDIDATE，不能用日曆截止日推估發布日來升版。

## 已建置
- `research/disclosure_pit_gate.py`：離線資料證據格式與 PIT 漏洞否決，支援「月營收」與「財報」事件。時間必須為含時區的 ISO8601，且同時滿足 `published_at <= observed_at <= decision_at`。來源、時間精度、交易所及事件類型必須完整，任何來源真實性仍需獨立驗證。**輸出固定 production_signal=false**。
- 實際官方最新彙總來源探針：上市 `https://openapi.twse.com.tw/v1/opendata/t187ap05_L`；上櫃 `https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O`。僅記錄 HTTP 狀態、資料量、JSON 格式與欄位，**不假裝資料表日期是逐公司實際公告時間**。
- `tests/test_disclosure_pit_gate.py`：正常時序、未發布資料、後補資料、月表日期替代時間、缺漏與時區安全測試。
- GitHub Actions：PR 自動測試、可手動觸發；無每月排程，無授權即時監控，無自動下單。

## 最小事件證據輸入
```json
{
  "symbol": "2330",
  "event_type": "MONTHLY_REVENUE",
  "period": "2026-10",
  "market": "TWSE",
  "published_at": "2026-11-06T18:35:00+08:00",
  "published_at_source": "official issuer publication timestamp",
  "observed_at": "2026-11-06T18:40:00+08:00",
  "timestamp_precision": "MINUTE",
  "evidence_kind": "VERIFIED_EXCHANGE_FILING",
  "source_url": "https://example.org/evidence"
}
```
**以上只是結構範例，不代表台積電真實公告時間或來源已驗證。禁止把範例拿來回測。**

## 必須繼續解決
1. 找出官方或獲授權提供的**公司逐筆歷史實際發布時間**且可對照來源檔案；財報公開時間與重大訊息發布時間須分開驗證，不能認定同時間。
2. 如果歷史時間不可得：從現在起記錄官方原文與首次觀測時間，啟用保守的前瞻訊號日；首次觀測時間只證明「不晚於該時點已被看見」，不是實際發布時刻。此時只能做前瞻資料庫，不可倒灌成歷史公開時間。
3. W1/W4 以原凍結規則重跑正確 PIT 的新樣本、完整成交及0.45/0.65%成本，失效股票、取消事件與未成交也須入帳。
4. 完成樣本外、逐步向前、兩種市場環境、200筆可評估獨立樣本與至少20未來交易日等適用治理門檻，再提交 W0/P0-G；不得直接上 Production。
5. 正式服務的 MCR/ETF 研究卡片仍為唯讀，Cloud Run 六模型首頁部署屬獨立工作，目前尚未驗收。

## 與既有模型
不新增月營收模型或改動 Revenue MoM 5D 的選股門檻；這個工具專注 Gate 0 資料證據，供事件策略復用，不能替代完整回測與投資組合驗證。
