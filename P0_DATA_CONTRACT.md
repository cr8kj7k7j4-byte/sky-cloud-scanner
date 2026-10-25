# P0-DATA Data Contract v1.1

Status: Production governance contract

## Purpose
Prevent unit, timestamp, semantic-type, freshness, duplication, causality and derived-field errors from reaching research or production decision layers.

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
4. low <= open/high/low/close consistency must hold.
5. Turnover derived from Fugle 5m candles must use:
   close_twd * volume_lots * 1000.
6. Any source-specific unit conversion must be explicit in code, not implied.
7. Research code may not silently redefine source units.
8. Source timestamps later than the decision/observation timestamp are invalid.
9. Duplicate canonical keys must be detected, not silently retained.
10. Required fields must expose missingness explicitly.
11. Source freshness must be evaluated against a documented SLA where an SLA exists.
12. Data lineage must identify the upstream source and quality-evaluation time.
13. A degraded source or causality violation must not be represented as HEALTHY.
14. UNKNOWN source facts must remain UNKNOWN rather than being guessed or proxied.

## Unified data-quality envelope
Implementation: src/data_quality.py

The governed envelope reports at least:
- missing_count
- duplicate_count
- bad_tick_count
- future_row_count
- latest_source_timestamp
- source_age_seconds
- freshness_threshold_seconds
- freshness_ok
- source_health
- decision_eligible
- errors
- lineage

A quality envelope is an engineering gate. It does not create or modify a trading signal.

## Source-health contract
Implementation: src/source_health.py

Each source-health result must retain:
- source
- observed_at
- source_timestamp
- age_seconds
- freshness SLA
- record count / minimum coverage when applicable
- explicit degradation reasons
- raw source error when one exists

## Market-calendar contract
Implementation: src/market_calendar.py

A session record must retain:
- session date
- market
- trading-day flag
- open/close time
- source
- source_as_of
- note

Weekday inference alone is not sufficient for a production trading calendar.

## Corporate-action / symbol-continuity contract
Implementation: src/corporate_actions.py

Corporate actions must preserve:
- symbol
- action type
- effective date
- official source
- source_as_of
- old/new symbol mapping where applicable
- split/conversion ratio where applicable
- cash amount where applicable
- notes

Symbol changes must be represented as explicit continuity mappings rather than destructive rewrites of historical identifiers.

## Revenue PIT special rule
Historical revenue features require verified publication timestamps.
If Historical verified MOPS filing timestamp coverage is 0%, affected revenue features remain BLOCKED / PRE_PIT_CANDIDATE.

Forbidden:
- statutory filing deadline used as publication timestamp proxy
- today's known filing used to backfill a historical decision timestamp
- lowering PIT standards because a backtest performs well

## Governance
- Base unit contract: src/data_contract.py
- Unified DQ: src/data_quality.py
- Source health: src/source_health.py
- Market calendar: src/market_calendar.py
- Corporate actions: src/corporate_actions.py
- CI tests: tests/test_data_contract.py and W3 engineering tests
- Workflows: .github/workflows/test-p0data.yml and .github/workflows/test-w3-engineering.yml
- Changes to units, timestamp semantics or PIT rules require code review plus test updates.
