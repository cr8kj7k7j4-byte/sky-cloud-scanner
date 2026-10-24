# P0-DATA Data Contract v1.0

Status: Production governance contract

## Purpose
Prevent unit, timestamp, semantic-type, and derived-field errors from reaching research or production decision layers.

## Required unit conventions
- Price: TWD/share
- Fugle historical 5m volume: lot
- Standard board-lot conversion: 1 lot = 1000 shares
- Turnover: TWD
- Returns/spreads: percent
- Timestamp: Asia/Taipei or explicit timezone-aware source timestamp
- VWAP: TWD/share with retained calculation window
- EPS: TWD/share
- Revenue: TWD

## Mandatory invariants
1. No negative volume.
2. OHLC prices must be positive.
3. high >= open/low/close.
4. low <= open/high/close.
5. Turnover derived from Fugle 5m candles must use:
   close_twd * volume_lots * 1000.
6. Any source-specific unit conversion must be explicit in code, not implied.
7. Research code may not silently redefine source units.

## Governance
- Contract implementation: src/data_contract.py
- CI tests: tests/test_data_contract.py
- Workflow: .github/workflows/test-p0data.yml
- Changes to units require code review plus test updates.
