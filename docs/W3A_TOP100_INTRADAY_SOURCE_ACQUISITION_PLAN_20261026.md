# W3A Source Status — Top100 Velocity Full-Market Intraday Data

Date: 2026-10-26
Status: CORE_BASELINE_SOURCE_PASS / NO_PURCHASE_REQUIRED

## Resolution

The corrected PIT whole-universe Fugle 5-minute source now passes the historical coverage gate for Baseline A.

Canonical evidence:
- reconciliation workflow 40221377923;
- 2,022 symbols with bars;
- symbol coverage 99.8519%;
- symbol-day coverage 98.9071%;
- minimum daily coverage 97.3726%;
- 54,187,242 retained bars;
- zero duplicate/conflicting/out-of-membership bars.

The prior 100-symbol artifact is superseded for this research purpose.

## Consequence

No new paid source is required to answer the first structural question:

> Does causal Dynamic Top100 + Velocity have positive after-cost intraday edge?

Historical bid/ask/order-book data is not required for Baseline A. Execution microstructure remains a later W6 gate and missing empirical spread/slippage/fill data must never be imputed to zero.

## Purchase policy

Do not purchase TWSE/TPEx custom historical microstructure or another vendor merely to run Baseline A.

A paid source may be reconsidered only if a surviving candidate reaches a later execution/capacity question that cannot be answered with current evidence.

Any paid purchase still requires explicit user approval.
