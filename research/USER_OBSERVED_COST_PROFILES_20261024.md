# User-observed Trading Cost Profiles

Date added: 2026-10-24

## Source basis

These profiles are calibrated from the user's actual brokerage transaction statements supplied in chat.

They are **user-specific empirical cost profiles**, not general statutory or market-wide rates.

## Profile 1 — CASH_DAYTRADE

Observed trade:
- Symbol: 2409 友達
- Shares: 1,000
- Buy: 36.05
- Sell: 35.90
- Buy commission: 12 TWD
- Sell commission: 12 TWD
- Sell transaction tax: 53 TWD
- Pure price P/L: -150 TWD
- Realized P/L: -227 TWD

Calibration:
- commission center: 0.0333% per side
- sell tax: 0.15%

## Profile 2 — MARGIN_FINANCING

Observed trade:
- Symbol: 2409 友達
- Shares: 1,000
- Buy: 37.05
- Sell: 35.90
- Buy commission: 12 TWD
- Sell commission: 12 TWD
- Sell transaction tax: 107 TWD
- Financing interest: 13 TWD
- Pure price P/L: -1,150 TWD
- Realized P/L: -1,294 TWD

Calibration:
- commission center: 0.0333% per side
- sell tax: 0.30%
- financing interest: **not fixed**; the observed 13 TWD is retained only as a sample

## Governance

1. Rounded statement fees mean the underlying brokerage rate cannot be inferred exactly from one trade.
2. Therefore 0.0333% is stored as a stable empirical center, not a claimed contractual rate.
3. Financing interest must be supplied per trade or derived from a validated holding-period interest model.
4. Slippage, spread, liquidity penalty and fill probability remain unknown until measured.
5. Execution RR must remain incomplete when those inputs are unknown.
6. The profiles may be replaced or versioned when more brokerage statements are collected.
