# W7 Evidence Dossier — Overnight → Opening Reversal

## Name
Overnight-to-First-Half-Hour Reversal

## Type
Intraday timing / opening price discovery / reversal

## Source
Iwanaga & Sakemoto (SSRN, 2025 posted; revised 2026)

## Market
U.S. market indices in source study; proposed transfer test to Taiwan.

## Core method
Test whether overnight return negatively predicts the first half-hour return, with volatility-state conditioning.

## Empirical strength
MEDIUM.
The source reports a clear negative predictive relationship and stronger effects in high-volatility periods, but it is one study focused on U.S. indices.

## OOS
Not treated by W7 as promotion-grade OOS evidence for Taiwan. Taiwan requires new pre-registered OOS.

## Transaction cost
External finding is not sufficient for Sky's cost gate. Sky must apply 0.45% primary and 0.65% stress if converted to a tradable rule.

## Replicability
HIGH for Taiwan because required inputs are simple and PIT-observable:
- prior close
- next open
- first 5/15/30m bars
- market/sector benchmark
- volatility state

## Taiwan transfer logic
Potentially plausible due to:
- overnight information accumulation
- opening auction
- daily price limits
- heavy retail participation
- possible opening overreaction / repricing
But these same institutional differences may change or destroy the effect, so transfer cannot be assumed.

## Sky overlap
LOW.
Not a frozen breakout family and not fixed-time cross-sectional ranking. Structural novelty is the overnight information state and opening repricing target.

## Data requirement
Fugle/TWSE minute stock/index data. Fugle stock minute history is available from 2023-05-23.

## Estimated integration cost
LOW-MEDIUM.

## Main risks
- opening-auction implementation detail
- extreme-gap/event concentration
- price-limit effects
- data timing leakage
- effect may only exist in high-vol regimes

## Worth buying?
NO dedicated data purchase is needed for first test.

## Worth testing?
YES.

## Handoff
W5 → W2 if accepted.

## Status
SEND_TO_W5
