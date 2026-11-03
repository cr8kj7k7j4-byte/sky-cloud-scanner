# Sky 三大統一指令｜操作手冊（2026-11-03）

## 入口

| 聊天指令 | GitHub workflow_dispatch 選項 | 預期用途 |
| --- | --- | --- |
| `Sky 全市場掃描` | `all_market` | 當沖主掃描 + Swing 與 5D 研究候選；空方策略未經驗證可執行器時明列未執行 |
| `Sky 系統健康檢查` | `system_health` | 富果／其他來源診斷、GitHub 排程健康稽核 |
| `Sky 全模型驗證` | `model_validation` | 正式登錄、研究凍結清冊、驗證規範與路由測試；不是完整績效回測 |

Workflow: [Sky Unified Commands](../.github/workflows/sky-unified-commands.yml)

## 如何執行

在 GitHub Actions → Sky Unified Commands → Run workflow 選擇 `command`，三個選項分別為 `all_market`、`system_health`、`model_validation`。

另一種可審計的觸發方式是在 main 更新 `scan_requests/unified/latest.json`，例如 `{"command":"system_health"}`；Push 會觸發同一套 Workflow。這是 GitHub 觸發，不是 ChatGPT 排程，沒有新增定時排程。

## 檢查成果

每次執行會保留 `sky-unified-<run_id>` Artifact，主要檔案在 `output/unified/<mode>.json` 和 `output/unified/summary.md`。點選該次 Actions Run → Artifacts 下載查看。

- `all_market`：只在官方交易日判斷通過後嘗試掃描；盤中報價及完整度仍以各掃描器實際輸出為準。Swing / Swing5D 只供研究，不得直接產生交易。
- `system_health`：流程成功不保證各資料權限均正常，必須閱讀來源診斷及排程稽核產物。
- `model_validation`：只核對治理與路由，不代表正期望、樣本外、成交品質或 Production 升版通過。

## 風控

不得自動下單。禁止研究策略繞過 P0-C、P0-R 或 P0-G。空方執行器未經正式確認時輸出 `NOT_EXECUTED_NO_VERIFIED_STANDALONE_RUNNER`，不得偽造空方評分或交易信號。缺資料、價格過期或失敗時保持 UNKNOWN / 禁止交易，不以舊行情補上即時價格。

Production 仍為 Sky Day Trading v1.4 / P0-C MVP 與 Sky Swing V1.0。
