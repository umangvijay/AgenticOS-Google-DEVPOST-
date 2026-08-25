terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable APIs
resource "google_project_service" "firestore" {
  service = "firestore.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  service = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudrun" {
  service = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "pubsub" {
  service = "pubsub.googleapis.com"
  disable_on_destroy = false
}

# 2. Firestore Database (Native mode)
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = "nam5" # Multi-region US
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.firestore]
}

# 3. Secret Manager: Master Key
resource "google_secret_manager_secret" "master_key" {
  secret_id = "SECRETS_MASTER_KEY"
  replication {
    auto {}
  }
  depends_on = [google_project_service.secretmanager]
}

# 4. Secret Manager: Gemini API Key
resource "google_secret_manager_secret" "gemini_key" {
  secret_id = "GEMINI_API_KEY"
  replication {
    auto {}
  }
  depends_on = [google_project_service.secretmanager]
}

# Note: Cloud Run services themselves are typically deployed via CI/CD (e.g. Cloud Build or deploy.sh)
# rather than Terraform because they iterate rapidly. This TF module handles the stateful foundation.
