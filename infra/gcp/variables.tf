variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Cloud Run / Memorystore / Artifact Registry region"
  type        = string
  default     = "asia-east1"
}

variable "scheduler_region" {
  description = "Cloud Scheduler region"
  type        = string
  default     = "asia-east1"
}

variable "artifact_repository" {
  type    = string
  default = "sky-scanner"
}

variable "container_image" {
  description = "Full Artifact Registry image URL with immutable tag or digest"
  type        = string
}

variable "job_name" {
  type    = string
  default = "sky-cloud-scanner"
}

variable "network_name" {
  type    = string
  default = "sky-vpc"
}

variable "subnet_name" {
  type    = string
  default = "sky-run-subnet"
}

variable "subnet_cidr" {
  type    = string
  default = "10.42.0.0/26"
}

variable "redis_name" {
  type    = string
  default = "sky-monitor-state"
}

variable "redis_tier" {
  description = "BASIC for lower cost; STANDARD_HA only after HA is required"
  type        = string
  default     = "BASIC"
}

variable "redis_memory_gb" {
  type    = number
  default = 1
}

variable "runtime_service_account" {
  type    = string
  default = "sky-runner"
}

variable "scheduler_service_account" {
  type    = string
  default = "sky-scheduler"
}

variable "fugle_secret_id" {
  description = "Existing Secret Manager secret ID containing FUGLE_API_KEY"
  type        = string
  default     = "FUGLE_API_KEY"
}

variable "paper_bucket_name" {
  description = "Optional globally unique GCS bucket name for Paper Trading ledger"
  type        = string
  default     = ""
}

variable "paper_retention_days" {
  description = "Delete Paper Trading run objects after this many days"
  type        = number
  default     = 90
}
