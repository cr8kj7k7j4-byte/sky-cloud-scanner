# W7 Evidence Dossier — Taiwan Broker / Branch Flow

## Name
Broker-Identity / Skill-Conditioned Flow

## Type
Taiwan-specific flow / identity information

## Market
TWSE / TPEx

## Core method
Different brokers/branches may carry different information content. Estimate any broker/branch "skill" or informational value using past-only rolling/expanding windows, then test future residual returns.

## Empirical strength
MEDIUM.
External Taiwan research suggests broker identity/order-flow aggregation can contain information, but W7 does not treat this as established production alpha.

## OOS
Requires strict fresh OOS after any branch-skill construction.

## Transaction cost
Must be tested at 0.45% / 0.65% if used for trading.

## Replicability
Technically possible but economically constrained by data access.

## Official data facts
TWSE e-shop full-market buy/sell daily report:
- start date 2012-10-25
- daily frequency
- security code / broker / transaction price / buy shares / sell shares
- generated after close
- full-market excluding warrants: NT$80,000/month internal-use list price
- certain proprietary trading is aggregated into head office

## Sky overlap
LOW.
Sky does not currently have broker-identity-conditioned flow.

## Data requirement
Daily broker/branch historical flow plus PIT branch-code mapping.

## Estimated integration cost
HIGH due data procurement, cleaning and branch continuity.

## Main risks
- cost
- broker branch-code lifecycle
- hidden aggregation rules
- full-sample "skill" leakage
- branch clientele drift
- not intraday despite flow intuition

## Worth buying?
DO_NOT_BUY NOW.

## Worth testing?
YES only after sample/schema feasibility and W5 acceptance.

## Handoff
W5 → W3 data feasibility → W1/W2 depending horizon.

## Status
SEND_TO_W5
