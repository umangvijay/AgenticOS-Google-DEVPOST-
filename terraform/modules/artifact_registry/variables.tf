variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "region" {
  type        = string
  description = "GCP Region"
}

variable "deploy_sa_email" {
  type        = string
  description = "Service account email that pushes images"
}
