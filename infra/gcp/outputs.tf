output "artifact_repository" {
  value = google_artifact_registry_repository.sky.name
}

output "cloud_run_job" {
  value = google_cloud_run_v2_job.sky.name
}

output "redis_host" {
  value     = google_redis_instance.sky.host
  sensitive = true
}

output "scheduler_jobs" {
  value = { for k, v in google_cloud_scheduler_job.scan : k => v.name }
}

output "paper_ledger_bucket" {
  value = google_storage_bucket.paper_ledger.name
}
