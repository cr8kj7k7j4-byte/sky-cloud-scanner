# W3B Production Runtime Inventory — 2026-10-25

Status: ACTIVE engineering inventory  
Scope: Runtime / deployment / CI / observability only. No Alpha logic changes.

## Runtime classification

| Runtime | Status | Evidence | Role |
|---|---|---|---|
| GitHub Actions | ACTIVE | `.github/workflows/scan.yml` has the formal intraday schedule and executes `python -m src.main` | PRIMARY CURRENT RUNTIME |
| Google Cloud Run Job | DEFINED / NOT YET VERIFIED LIVE | `infra/gcp` defines Artifact Registry -> Cloud Run Job -> Redis -> Scheduler | PRIMARY CANDIDATE |
| Railway | NOT DEPLOYED | Connected Railway account currently has zero projects | DEPRECATED / UNUSED |

## Current production identity

- Repository: `cr8kj7k7j4-byte/sky-cloud-scanner`
- Branch: `main`
- Deployment source currently evidenced: GitHub Actions
- Scanner entrypoint: `python -m src.main`
- Formal schedule timezone: `Asia/Taipei`
- Formal scan times: 09:05, 09:15, 09:30, 09:50, 10:15 on weekdays

A Cloud runtime must not be labeled PRIMARY until project, service/job, region, current image digest/commit, execution health, last deployment, variables/secrets inventory, and error history are verified.

## Cloud Run model

Sky is intentionally modeled as a **Cloud Run Job**, not a continuously running HTTP service. The scanner executes a finite job and exits.

Therefore production health is defined by:

1. Job execution terminal status.
2. Exit code.
3. Output/artifact presence.
4. Data freshness.
5. E2E acceptance status.
6. Alert delivery status.
7. Ledger/outcome completeness.

An HTTP `/health` endpoint is not a mandatory health primitive for the batch scanner.

## Safety state

If mandatory realtime inputs are stale, unavailable, or fail data-quality gates, runtime must fail closed into `DATA_DEGRADED` / `NO_TRADE`; infrastructure fallback must never fabricate a tradable signal.

## Known blockers

- Google Cloud project/job is defined in Terraform but live runtime identity is not yet verified from the cloud control plane.
- Dependency ranges in `requirements.txt` are not fully pinned, so image rebuilds are not yet fully reproducible.
- Production deployment provenance must ultimately record repo, branch, commit SHA, image digest, environment, and deployment/execution ID.
