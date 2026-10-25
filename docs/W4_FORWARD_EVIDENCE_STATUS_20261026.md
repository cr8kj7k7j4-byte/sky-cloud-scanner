# W4｜Forward Shadow / Paper Evidence Status — 2026-10-26

## Formal status

**WAITING_FOR_FIRST_ELIGIBLE_SCAN**

Production impact: **NONE**

Current Production remains unchanged.

## Evidence activation

Canonical forward ledger activation:
- 2026-10-24T23:28:08Z
- Asia/Taipei: 2026-10-25 07:28:08

No pre-activation artifact may be relabeled as new forward W4 evidence.

## Trading-calendar status

2026-10-26 is an official TWSE market holiday (observed holiday for Taiwan Retrocession / Kinmen Guningtou Victory Memorial Day).

Therefore any weekday-cron scanner workflow on 2026-10-26:
- does not create an eligible W4 scan unless a non-empty, valid post-ledger Paper record is actually produced;
- must not increment the eligible scan count merely because the GitHub Actions workflow succeeds.

Canonical holiday reference:
- https://www.twse.com.tw/zh/trading/holiday.html

Next ordinary weekday eligible for forward collection after this status date:
- 2026-10-27, subject to actual market/data availability.

## Automated forward pipeline

Trading-day scanner schedule (Asia/Taipei):
- 09:05
- 09:15
- 09:30
- 09:50
- 10:15

Post-market:
- 14:30 Shadow outcome backfill
- 14:50 W6 forward L1/execution evidence
- 16:30 Shadow promotion dashboard

## W4 eligibility rule

A workflow success alone is not evidence.

An eligible scan requires:
1. Paper artifact exists.
2. At least one valid record exists.
3. Observation timestamp is on/after ledger activation.
4. Symbol is non-empty.

Machine audit:
- research/w4_scan_artifact_eligibility.py

## Sufficiency gate

W4 remains WAITING until all are true:
- >= 200 evaluable observations
- >= 20 trading days
- >= 2 market regimes
- outcome completeness >= 95%
- single-symbol share <= 20%

These are evidence sufficiency thresholds, not win-rate or profitability probabilities.

## Downstream gates

After sample sufficiency:
1. Portfolio / cost / capacity evidence
2. P0-R review
3. W6 observed execution/slippage/fill evidence
4. W3B forward-evidence pipeline reliability
5. W0 / P0-G governance review

No Small Live authorization exists at this stage.
