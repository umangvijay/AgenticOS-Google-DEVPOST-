variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "worker_endpoint" {
  type        = string
  description = "Cloud Run Worker URL for push subscription"
}

variable "worker_sa_email" {
  type        = string
  description = "Service account email of the worker, used for OIDC authentication on Push"
}
