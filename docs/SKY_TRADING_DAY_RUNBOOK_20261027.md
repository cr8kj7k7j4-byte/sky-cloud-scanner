# Sky 2026-10-27 Trading-Day Runbook

- Authority: W0｜Sky Master Control / P0-G
- Trading date: 2026-10-27
- Mode: PRODUCTION-ONLY / MANUAL-EXECUTION
- Production impact: NONE; this runbook does not change Alpha rules.
- Live auto-execution: DISABLED

## 1. Objective

Ensure Sky has one operationally usable strategy for the next trading day without allowing unfinished research, proxy backtests, or open PRs to leak into live decisions.

## 2. Strategy authorization for 2026-10-27

### New intraday entries
AUTHORIZED strategy baseline:
- Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP

Research candidates are NOT authorized for real-money entry:
- W2 Opening Acceleration Baseline C
- W2 Opening Retest/Reclaim Baseline D
- Overnight Reversal
- Dynamic Lead-Lag
- Broker Flow
- any W5/W7 candidate
- any open/unmerged PR

### New Swing entries
TEMPORARILY HOLD.

Reason:
- canonical PIT daily data readiness is PASS;
- however Sky Swing V1.0 exact executable rule specification is BLOCKED_EXACT_RULE_SPEC;
- proxy/challenger research may not substitute for Production.

Existing Swing positions remain eligible for PMS risk management only.

## 3. Automated operating schedule

### 08:20 Asia/Taipei
Run:
- Sky Premarket Intelligence
Purpose:
- market/event context only;
- no direct buy signal.

### Intraday scans
- 09:05
- 09:15
- 09:30
- 09:50
- 10:15

Workflow:
- .github/workflows/scan.yml

Trading-calendar gate must be true before scan.

## 4. Mandatory decision chain

Market
→ Sector / Relative Strength
→ Stock
→ Setup
→ Trigger
→ Anti-Chase
→ RR Gate
→ P0-O Ranking
→ P0-R Risk
→ P0-C Decision
→ P0-A Monitoring
→ PMS / P0-L evidence

No single upstream signal authorizes entry.

## 5. New-entry hard gates

A candidate may be considered only when all applicable Production gates pass.

Minimum:
- valid current price
- price <= TWD 100 unless explicitly overridden by W0/user
- sufficient liquidity and trade value
- no material spread rejection
- no limit-up chase
- no P0-R BLOCK
- no P0-A BLOCKED / INVALIDATED
- traceable evidence eligible
- Production-eligible strategy
- trigger confirmed with price/volume/VWAP/structure
- after-cost RR >= 1.5; prefer >= 2.0
- no major Anti-Chase rejection

TRIGGERED != automatic buy.

## 6. Intraday risk discipline

- No averaging down.
- No loss-position add.
- Add only after position moves favorably and a second valid breakout/retest appears.
- Stop may only move toward lower risk.
- Two consecutive stops OR daily net loss reaches 2R => no further new entries that day.
- If 1R / account equity / max position are unknown, do not invent share quantity.
- Manual user execution remains required.

## 7. Classification

A+:
- data sufficient;
- setup and trigger confirmed;
- all hard gates pass.

A:
- potentially valid but trigger or evidence incomplete.

X:
- rejected / no trade.

If no A+ candidate exists:
「目前沒有符合條件的新進場標的。」

## 8. Tomorrow-specific research separation

The following may continue in Shadow/Research only:
- W1 canonical Swing validation work
- W2 candidate backtests
- W3A PIT data work
- W4 evidence accumulation
- W5/W7 candidate intake
- W6 execution research

None of these may overwrite the 2026-10-27 Production-only trading baseline without W0/P0-G promotion review.

## 9. Mobile decision output

For any candidate surfaced during the day, user-facing output should begin with:
- 🟢 可執行
- 🟡 等待／觀察
- 🔴 禁止交易／停損／退出

Then show:
股票、資料時間、現價、方向、多方評分、空方評分、買進點、最高接受價、加碼點、停損、第一目標、第二目標、風險報酬、現在動作。

## 10. Governance note

This runbook creates operational clarity, not a profitability guarantee.
Research HOLD does not disable the current intraday Production baseline.
Swing new-entry HOLD is a provenance safeguard until the exact frozen V1.0 rule specification is recovered/governed.
