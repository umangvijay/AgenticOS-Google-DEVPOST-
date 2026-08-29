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
    APP_ENV                  = "production"
    LOG_LEVEL                = "INFO"
    STORAGE_BACKEND          = "firestore"
    GEMINI_MODEL             = "gemini-3.6-flash"
    GEMINI_EMBEDDING_MODEL   = "gemini-embedding-2-preview"
    CONTACT_TO_EMAIL         = "godumang35@gmail.com"
    CONTACT_SMTP_HOST        = "smtp.gmail.com"
    CONTACT_SMTP_PORT        = "587"
    CONTACT_SMTP_USERNAME    = "godumang35@gmail.com"
  }
}
