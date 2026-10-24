# User-observed Trading Cost Profiles

Date added: 2026-10-24

## Source basis

These profiles are calibrated from user-supplied brokerage statements.

They are **user-specific empirical cost profiles**, not general statutory or market-wide rates.

No transaction-level brokerage detail should be stored in this public repository.

## CASH_DAYTRADE profile

Anonymous calibration:
- commission center: 0.0333% per side
- sell tax observed: 0.15%
- observed sample count: 1

## MARGIN_FINANCING profile

Anonymous calibration:
- commission center: 0.0333% per side
- sell tax observed: 0.30%
- financing interest: per-trade / holding-period input required
- observed sample count: 1

## Governance

1. Rounded statement fees mean the underlying brokerage rate cannot be inferred exactly from one trade.
2. 0.0333% is stored as a stable empirical center, not a claimed contractual rate.
3. Financing interest must be supplied per trade or derived from a validated holding-period model.
4. Slippage, spread, liquidity penalty and fill probability remain unknown until measured.
5. Execution RR must remain incomplete when those inputs are unknown.
6. Raw brokerage records belong in `output/private/`, which is git-ignored.
7. Only anonymous aggregate calibration parameters may be committed to the public repository.
8. Profiles must be versioned as more samples accumulate.
