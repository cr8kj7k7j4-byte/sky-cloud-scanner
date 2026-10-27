# Sky Mobile Result Table Contract v1.0

Status: Production presentation contract  
Date: 2026-10-27

## Canonical table

All current-state Sky scan/update outputs should prioritize this table when there is one or more stock candidate:

| 股票 | 現價 | 方向 | 多方評分 | 空方評分 | 買進觸發 | 最高接受價 | 停損／失效 | 分類 | 現在動作 |
|---|---:|---|---:|---:|---|---:|---|---|---|

Applies to:
- Sky 快掃
- Sky 當沖現在掃一次
- Sky Swing 5D 快掃
- Sky 波段現在掃一次
- Sky 波段快掃
- Sky Swing V1.1｜現在掃一次
- single-stock update / full analysis where the same fields are meaningful
- position/alert output may reuse the table, while position-specific P&L fields remain separate

## Field rules

- 現價: newest obtainable quoted price; include a data timestamp outside the table.
- 方向: evidence direction, not a prediction guarantee.
- 多方評分 / 空方評分: 0–100 evidence-comparison scores; never call them probability or win rate.
- 買進觸發: must be conditional. If no governed trigger exists, use "無有效多方觸發" or a clear non-executable description.
- 最高接受價: must be "—" when no governed max-entry rule exists. Never invent one to complete the table.
- 停損／失效: governed stop/invalidation only. If unavailable, "—".
- 分類: A+ / A / X only.
- 現在動作: only 買進 / 等待 / 觀察 / 續抱 / 加碼 / 減碼 / 停損 / 退出 / 禁止交易.

## Score governance

Display evidence scores are presentation-only and:
- are NOT statistical probabilities;
- are NOT historical win rates;
- do NOT feed P0-O ranking;
- do NOT feed P0-C decisions;
- do NOT feed P0-R sizing/risk;
- do NOT change Alpha, Trigger, Stop, Target or Promotion state.

If observable inputs are insufficient, show "—" rather than fabricate a score.

## V1.1 special rule

Sky Swing V1.1 keeps its frozen D-close signal / D+1-open entry semantics.
If the D+1 opening entry window has already passed:
- 買進觸發: show the original D+1 open and "(已過，不追)";
- 現在動作: 禁止交易;
- current intraday price must never be rewritten into a new trigger.


## Quick-scan emphasis v1.1

所有快掃／掃一次輸出固定採 10 欄表格。股票、現價、分類、現在動作以粗體呈現；多空評分差距達 10 分以上時，較強一側以粗體呈現；沒有治理後價位時顯示 —，不得補假數字。
