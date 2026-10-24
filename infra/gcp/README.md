# Sky on Google Cloud

This directory defines the production-infrastructure candidate for Sky V2.1.

## Architecture

GitHub / Cloud Build
→ Artifact Registry
→ Cloud Run Job
→ P0-S / P0-R / P0-A
→ Memorystore for Redis
→ Cloud Scheduler

The scanner is modeled as a **Cloud Run Job**, not a Cloud Run Service, because
`python -m src.main` performs a finite scan and exits.

## Scheduled runs

Timezone: `Asia/Taipei`

- 09:05
- 09:15
- 09:30
- 09:50
- 10:15

Cloud Scheduler provides at-least-once delivery, so Sky execution must remain
idempotent. P0-A state keys should be replace/update state rather than
irreversible side effects.

## Redis / P0-A

Cloud Run Job uses Direct VPC egress to reach Memorystore over its private IP.

Runtime environment:

- `MONITOR_STATE_BACKEND=redis`
- `REDIS_URL=redis://<memorystore-private-ip>:6379/0`
- `MONITOR_STATE_REDIS_KEY=sky:p0a:monitor_state`

## Secrets

Do **not** put API keys in Terraform variables or `.tfvars`.
Create `FUGLE_API_KEY` in Secret Manager first. The Cloud Run runtime service
account receives `roles/secretmanager.secretAccessor`.

## Safety / promotion rule

Infrastructure readiness does not promote P0-S into a production trading
signal. `production_eligible=false` remains authoritative until OOS,
cost/slippage stress, Paper Trading, and governance gates pass.

## Apply prerequisites

Before `terraform apply`, supply at minimum:

- `project_id`
- `container_image`

Example only:

```hcl
project_id      = "YOUR_PROJECT_ID"
container_image = "asia-east1-docker.pkg.dev/YOUR_PROJECT_ID/sky-scanner/sky-cloud-scanner@sha256:..."
```

Review projected Google Cloud cost before applying. Memorystore is billable and
should not be created solely to test syntax.
