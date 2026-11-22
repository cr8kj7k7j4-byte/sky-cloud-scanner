# Legacy evidence / cadence extraction (2026-11-22)

Preserved from:
- `governance/shadow-readiness-portfolio-contract`: `src/shadow_evidence.py`, its test and dashboard integration (legacy PR #69).
- `research/paper-only-p0r-cadence-acceptance-20261110`: `research/sky_paper_only_acceptance.py`, its test (legacy PR #496).

The only retained capabilities are:
1. Distinguish zero eligible scans (waiting) from missing scan artifacts / unreadable zero-row results.
2. Validate timezone-aware market-source timestamps.
3. Enumerate 55 expected five-minute Taiwan research slots (09:00–13:30 inclusive).
4. Assess verified slot observations without assuming that an on-demand scan is a scheduled run.

Removed by design: all paper-ledger inputs, paper fills, assumed order execution, hypothetical P&L, Shadow promotion eligibility, simulated-cost evidence, and any automatic trading.

Original branch histories must still be retained until a separate whole-branch and workflow-reference audit is complete. This is an extracted research implementation, not proof of parity with existing main, production readiness, or successful live-market validation.

2026-11-23 acceptance should verify the main SHA and scan run ID, matching artifact and source timestamps, real 5-minute candles and VWAP provenance, paid-API deduplication, and phone same-run readback. These checks are standalone and NOT connected to live workflows.

References:
- https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/69
- https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/496
