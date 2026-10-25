# Historical Point-in-Time Universe Contract v1.0

Status: Production research-governance foundation

## Why this exists
A current-listing universe must not be used to represent the investable universe of a historical date.
Doing so introduces survivorship and future-listing bias.

## Canonical membership rule
A symbol is eligible on date D only when:
- listed_from <= D
- and listed_to is null OR D <= listed_to

Membership must be reconstructed from official listing / delisting / market-transfer events.

## Required event fields
- symbol
- exchange
- name
- listed_from
- listed_to
- source
- source_as_of
- notes

## Required edge cases
- delisted companies remain present before their delisting date
- newly listed companies are absent before listing date
- TWSE <-> TPEx market transfers create separate intervals
- relisting creates a new interval
- overlapping intervals on the same exchange are invalid

## Governance rule
Historical backtests claiming OOS / walk-forward validity must not use
research/build_universe_sample.py current-listing samples as their final production evidence.

The current 50 TWSE + 50 TPEx deterministic sample remains useful only for
research engineering and regression testing.

## Files
- Engine: src/point_in_time_universe.py
- Tests: tests/test_point_in_time_universe.py
- CI: .github/workflows/test-point-in-time-universe.yml

## Source requirement
Production interval data must come from verified official TWSE / TPEx / MOPS records.
Unknown delisting dates must remain UNKNOWN rather than being guessed.
