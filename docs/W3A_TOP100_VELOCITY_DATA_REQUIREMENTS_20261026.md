# W3A Data Requirements — Top100 Velocity Baseline A

Date: 2026-10-26
Status: CORE_REQUIREMENTS_PASS

## Objective

Enable causal reconstruction of the rolling Top100 gainers universe and a fixed-horizon acceleration test.

## Required historical fields

Available from corrected PIT whole-universe 5m source / PIT ledger:
- symbol;
- exchange;
- 5m bar timestamp;
- open/high/low/close;
- interval volume;
- cumulative transaction average where present;
- point-in-time listing membership.

Derived causally:
- prior-session close;
- current-day return;
- full-market gain rank;
- Top100 membership;
- price velocity per minute;
- rank velocity per minute;
- interval volume rate;
- volume acceleration;
- next-bar entry;
- 30-minute MFE / MAE / exit outcome.

## Governance

- completed bars only for features;
- no end-of-day rank backfill;
- no current-universe backward substitution;
- no outcome field in decision features;
- 2026 is Research Test, not fresh OOS;
- historical empirical spread/slippage/fill is optional for Baseline A and remains a later W6 evidence gate.

Core source coverage now exceeds the >=95% gate, so W2 may execute the preregistered Baseline A test.
