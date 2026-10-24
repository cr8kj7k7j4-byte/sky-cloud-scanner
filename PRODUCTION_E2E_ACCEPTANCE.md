# Sky Production End-to-End Acceptance Contract v1.0

Status: Production-readiness acceptance suite

## Objective
Validate that Sky's existing modules behave consistently as one governed trading system. This is an engineering acceptance test, not evidence of trading profitability.

## Covered path
P0-DATA -> P0-M -> P0-F -> P0-S -> P0-O -> P0-R -> P0-X -> P0-A -> Shadow/Paper -> P0-L

P0-C production rule semantics are represented by the existing strategy/risk/monitor gates and must not be bypassed by ranking.

## Mandatory scenarios
1. Normal candidate:
   - market/features/strategy/ranking complete
   - P0-R allows
   - execution-cost RR gate passes
   - P0-A returns TRIGGERED/等待
   - research-only strategy remains SHADOW_OBSERVE, never auto-executes

2. Daily loss kill:
   - P0-R BLOCK
   - P0-A BLOCKED / 禁止交易

3. Anti-chase:
   - price above max_entry
   - P0-A INVALIDATED / 禁止交易

4. Missing execution assumptions:
   - must not be interpreted as zero cost
   - execution gate blocks

5. Outcome/Ledger:
   - deterministic outcome can be reproduced
   - costs reduce net P&L
   - R multiple and holding time are recorded

## Non-goals
- Does not validate Alpha.
- Does not promote any research-only model.
- Does not authorize real broker orders.
- Does not replace OOS, walk-forward, Point-in-Time, leakage or Paper/Shadow validation.
