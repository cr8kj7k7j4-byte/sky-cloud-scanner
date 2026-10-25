# W3B Production Hardening Gate — 2026-10-25

Status: ENGINEERING GATE  
Owner: W3B｜Sky Cloud & Production Engineering

## Mandatory pre-merge checks

1. Python compile succeeds.
2. Unit / integration regression succeeds.
3. Production E2E succeeds.
4. Docker image builds from repository root.
5. Container can import the production scanner entrypoint.
6. Container runtime is non-root.
7. Terraform formatting and validation succeed.
8. No trading Alpha semantics are changed by this gate.

## Deployment verification contract

A deployment is not considered verified until its provenance can be tied to:

- repository
- branch
- commit SHA
- immutable image digest where applicable
- environment
- deployment / execution ID
- terminal status
- observed timestamp

## Cloud Run Job health contract

Because Sky runs as a batch Job, healthy means:

- execution reaches terminal SUCCESS;
- scanner exits 0;
- mandatory outputs are present;
- data freshness gates are satisfied;
- no `DATA_DEGRADED` condition is being misreported as tradable;
- alert and ledger side effects are traceable.

## Rollback contract

Rollback must target a previously verified commit/image digest. A failed or unverified deployment must never become the rollback source.

## Current promotion rule

Engineering PASS does not promote or alter any trading strategy. Sky V2.1 Alpha and Production strategy state remain governed by W0/P0-G.
