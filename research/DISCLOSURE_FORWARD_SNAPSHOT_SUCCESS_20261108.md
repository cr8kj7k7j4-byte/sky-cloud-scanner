# 2026-11-08：四來源官方快照採集成功重跑與排程治理結論

## 操作結論
**SUCCESS / SOURCE_CAPTURE_PILOT_ONLY。** 此次 4/4 官方資料來源完成單次真實 API 擷取、bytes+SHA256+UTC 時間與 artifact 保存。**尚不啟用 cron、Production 或實盤。**

- 正式程式研究 PR #322：https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/322
- 成功工作流程：https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42417888034
- Artifact：https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42417888034/artifacts/13592675555

## 問題定位
- 前次 Run #42417305113 與 #42417403829：TWSE 成功，但 TPEx 回傳 HTTP 302；後一次已成功保留失敗證據、HTTP狀態，但整體測試依規 FAIL。
- **獨立定向診斷** Run #42417806752：同一 GitHub Runner 使用不跟隨轉址的標準 GET 檢查 TPEx 月營收、重大訊息及 Swagger，三端點全 HTTP 200，無轉址，故不能斷言網址永久失效。
- 本次新版本分隔多個官方請求、採用已成功的同格式標頭，並限制重試；Run #42417888034 四來源成功。**只能確認改善後此輪成功，不能證實302唯一根因，也不能當作未來每次必成功。**

## 實際成功取得的當次官方快照
| 來源 | HTTP | Rows | SHA256 |
|---|---|---:|---|
| TWSE revenue latest | 200 | 1,088 | `a58c04b3bdc2b94632027018ca4f09f6ad053848addb7b9580b372626542fc17` |
| TPEx revenue latest | 200 | 893 | `a27fea120daa8ef4543bcbf6e31426cad2e0201111ee8d97916fbb5fce2727a6` |
| TWSE material latest | 200 | 5 | `dc7e8ff888c5bdcb37096db725c9998ba626184193d00576dcb5be8336536b43` |
| TPEx material latest | 200 | 285 | `5c05988991a02cc81f2b86ffabcd5104f78c2f48904de736e5cc62e2d8f22453` |

HTTP 200、來源資料量、位元組雜湊與首次取得 UTC 時間是**可核對的工程證據**。
最新資料表內的「出表日期」仍非原始逐公司公告時刻。**historical_pit_event_count=0，source first observed at != published_at。**

## 避免在證據未成熟時擴張的下一階段
1. **持久儲存**：GCS bucket、IAM/OIDC 及物件版本/保留政策未確認；artifact 只保留短期，未驗證無法視為完整前瞻資料庫。
2. **跨日穩定度**：至少多個實際交易日，檢查來源完整率、回應耗時、API 403/302、超時、連線與去重；單次成功不代表排程可用。
3. **事件型態拆分**：收入彙總、重大訊息與財報原始公布時間互不等價；需逐則資料來源URL、原始公告時間、觀測時間與更正識別；僅達時間及來源審查者才可納入 PIT。
4. **歷史策略合格資料**：用已核實 PIT 的逐則月營收/財報資料串富果日K分K及固定未調整策略；成本0.45/0.65%、真實成交、風控與W0/P0-G不跳級。
5. **通知與排程**：在GCS+IAM+持久化 readback 驗證、故障告警、台灣時間換算與重複排程盤點後，才可啟用 GitHub Actions cron。這次沒有新排程，沒有 Cloud Run 部署。

## 本次狀態
- 程式／資料完整性測試：PASS。
- 官方來源單次採集：4/4 PASS。
- 原始資料短期 artifact 上傳：PASS。
- 長期GCS備份／真正原始公告時間：PENDING。
- 策略正期望及 Production：INSUFFICIENT_DATA，禁止升級。
