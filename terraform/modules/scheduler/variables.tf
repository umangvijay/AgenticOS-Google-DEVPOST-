variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "region" {
  type        = string
  description = "GCP Region"
}

variable "pubsub_topic_id" {
  type        = string
  description = "The Pub/Sub topic ID to publish scheduled events to"
}

variable "scheduler_sa_email" {
  type        = string
  description = "The service account email for the Cloud Scheduler to use"
}
