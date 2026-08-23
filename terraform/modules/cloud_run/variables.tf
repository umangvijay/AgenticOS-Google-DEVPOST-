variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "region" {
  type        = string
  description = "GCP Region"
}

variable "service_name" {
  type        = string
  description = "Name of the Cloud Run service"
}

variable "image" {
  type        = string
  description = "Container image URL"
}

variable "service_account" {
  type        = string
  description = "Service account email to run the service as"
}

variable "min_instances" {
  type        = number
  default     = 0
}

variable "max_instances" {
  type        = number
  default     = 10
}

variable "timeout_seconds" {
  type        = number
  default     = 300
}

variable "concurrency" {
  type        = number
  default     = 80
}

variable "environment_vars" {
  type        = map(string)
  default     = {}
}

variable "secrets" {
  type        = map(string)
  description = "Map of ENV_VAR_NAME to Secret Version ID"
  default     = {}
}

variable "is_public" {
  type        = bool
  description = "Whether the service allows unauthenticated invocations"
  default     = false
}

variable "invoker_sa_emails" {
  type        = list(string)
  description = "List of service account emails allowed to invoke the service (if not public)"
  default     = []
}
