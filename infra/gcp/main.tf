terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  required_apis = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "cloudscheduler.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
  ])
  scan_schedules = {
    "0905" = "5 9 * * 1-5"
    "0915" = "15 9 * * 1-5"
    "0930" = "30 9 * * 1-5"
    "0950" = "50 9 * * 1-5"
    "1015" = "15 10 * * 1-5"
  }
}

resource "google_project_service" "apis" {
  for_each           = local.required_apis
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "sky" {
  location      = var.region
  repository_id = var.artifact_repository
  format        = "DOCKER"
  description   = "Sky Cloud Scanner container images"
  depends_on    = [google_project_service.apis]
}

resource "google_compute_network" "sky" {
  name                    = var.network_name
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "sky" {
  name          = var.subnet_name
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.sky.id
}

resource "google_redis_instance" "sky" {
  name               = var.redis_name
  tier               = var.redis_tier
  memory_size_gb     = var.redis_memory_gb
  region             = var.region
  redis_version      = "REDIS_7_2"
  authorized_network = google_compute_network.sky.id
  depends_on         = [google_project_service.apis]
}

resource "google_service_account" "runtime" {
  account_id   = var.runtime_service_account
  display_name = "Sky Cloud Run Job Runtime"
}

resource "google_service_account" "scheduler" {
  account_id   = var.scheduler_service_account
  display_name = "Sky Scheduler Invoker"
}

resource "google_project_iam_member" "runtime_secret_access" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "scheduler_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_run_v2_job" "sky" {
  name                = var.job_name
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1
    template {
      service_account = google_service_account.runtime.email
      timeout         = "600s"
      max_retries     = 0

      containers {
        image   = var.container_image
        command = ["python"]
        args    = ["-m", "src.main"]

        env {
          name  = "MONITOR_STATE_BACKEND"
          value = "redis"
        }
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.sky.host}:${google_redis_instance.sky.port}/0"
        }
        env {
          name  = "MONITOR_STATE_REDIS_KEY"
          value = "sky:p0a:monitor_state"
        }
        env {
          name  = "STRICT_OFFICIAL_MODE"
          value = "1"
        }
        env {
          name  = "ALLOW_MIS_OTC_FALLBACK"
          value = "1"
        }
        env {
          name  = "MAX_PRICE"
          value = "100"
        }
        env {
          name  = "TOP_N"
          value = "100"
        }
        env {
          name  = "DEEP_DIVE_N"
          value = "12"
        }
        env {
          name = "FUGLE_API_KEY"
          value_source {
            secret_key_ref {
              secret  = var.fugle_secret_id
              version = "latest"
            }
          }
        }
      }

      vpc_access {
        network_interfaces {
          network    = google_compute_network.sky.name
          subnetwork = google_compute_subnetwork.sky.name
        }
        egress = "PRIVATE_RANGES_ONLY"
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_project_iam_member.runtime_secret_access,
  ]
}

resource "google_cloud_scheduler_job" "scan" {
  for_each    = local.scan_schedules
  name        = "sky-scan-${each.key}"
  description = "Invoke Sky scanner at ${each.key} Asia/Taipei"
  schedule    = each.value
  time_zone   = "Asia/Taipei"
  region      = var.scheduler_region

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.sky.name}:run"
    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [
    google_cloud_run_v2_job.sky,
    google_project_iam_member.scheduler_run_invoker,
  ]
}
