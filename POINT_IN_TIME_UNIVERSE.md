# Historical Point-in-Time Universe Contract v1.1

Status: Production research-governance foundation

## Why this exists
A current-listing universe must not be used to represent the investable universe of a historical date.
Doing so introduces survivorship and future-listing bias.

The governing question is:
"At that historical moment, could the system actually have known this symbol, membership state and supporting data?"

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

## Corporate actions and symbol continuity
Listing intervals alone do not fully solve historical identity.

Production historical data must also preserve relevant corporate actions such as:
- symbol changes
- mergers / conversions where they alter identifier continuity
- splits / reverse splits when price/quantity continuity is affected
- cash distributions where adjusted-price research requires them

Symbol continuity must use explicit old_symbol -> new_symbol mappings with an effective date and official provenance.
Historical rows must not be destructively renamed as if the new symbol existed before the effective date.

Engineering contract:
- src/corporate_actions.py
- tests/test_corporate_actions.py

## Timestamp causality
Every historical membership or corporate-action fact must retain a source_as_of / publication-observation boundary sufficient to answer whether the system could have known it at the evaluated timestamp.

Unknown historical publication or effective timestamps remain UNKNOWN and may block promotion.
No legal-deadline proxy may be substituted for an unavailable publication timestamp when the strategy depends on actual availability.

## Governance rule
Historical backtests claiming OOS / walk-forward validity must not use
research/build_universe_sample.py current-listing samples as their final production evidence.

The current 50 TWSE + 50 TPEx deterministic sample remains useful only for
research engineering and regression testing.

## Files
- Universe engine: src/point_in_time_universe.py
- Corporate-action continuity: src/corporate_actions.py
- Universe tests: tests/test_point_in_time_universe.py
- Corporate-action tests: tests/test_corporate_actions.py
- CI: .github/workflows/test-point-in-time-universe.yml and .github/workflows/test-w3-engineering.yml

## Source requirement
Production interval and corporate-action data must come from verified official TWSE / TPEx / MOPS records.
Unknown delisting, effective or publication dates must remain UNKNOWN rather than being guessed.

