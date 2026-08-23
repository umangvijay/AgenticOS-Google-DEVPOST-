variable "project_id" {
  type        = string
  description = "Google Cloud Project ID for Dev Environment"
}

variable "region" {
  type        = string
  description = "Default GCP Region"
  default     = "us-central1"
}

variable "api_image" {
  type        = string
  description = "Docker image URL for the API service"
}

variable "worker_image" {
  type        = string
  description = "Docker image URL for the Worker service"
}

variable "shared_env_vars" {
  type        = map(string)
  description = "Environment variables shared across both API and Worker"
  default = {
    APP_ENV                = "dev"
    LOG_LEVEL              = "INFO"
    GEMINI_MODEL           = "gemini-1.5-pro"
    GEMINI_EMBEDDING_MODEL = "text-embedding-004"
  }
}
