variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "api_sa_email" {
  type        = string
  description = "Email of the API service account"
}

variable "worker_sa_email" {
  type        = string
  description = "Email of the Worker service account"
}
