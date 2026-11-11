# PR #523 live pull_request event smoke validation

This file exists ONLY on a temporary validation branch, to verify that the research-only static security evidence workflow merged into main triggers on a genuine pull_request event and emits an externally readable Artifact.

- Scope: documentation-only, no production strategy changes, no orders, no paid API.
- Not for merge into main; close test PR after evidence inspection.
- Required check: governance-e2e.
- Expected static preflight: deterministic report; governance_decision=HOLD; production_eligible=false.
