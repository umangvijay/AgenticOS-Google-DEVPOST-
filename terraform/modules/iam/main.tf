# API Service Account
resource "google_service_account" "api_sa" {
  account_id   = "agentos-api-sa"
  display_name = "AgenticOS API Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "api_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_project_iam_member" "api_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_project_iam_member" "api_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_project_iam_member" "api_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# Worker Service Account
resource "google_service_account" "worker_sa" {
  account_id   = "agentos-worker-sa"
  display_name = "AgenticOS Worker Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "worker_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}

resource "google_project_iam_member" "worker_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}

resource "google_project_iam_member" "worker_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}

resource "google_project_iam_member" "worker_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}

resource "google_project_iam_member" "worker_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}

# Scheduler Service Account
resource "google_service_account" "scheduler_sa" {
  account_id   = "agentos-scheduler-sa"
  display_name = "AgenticOS Scheduler Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "scheduler_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

# Deploy Service Account (CI/CD)
resource "google_service_account" "deploy_sa" {
  account_id   = "agentos-deploy-sa"
  display_name = "AgenticOS Deployment Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "deploy_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deploy_sa.email}"
}

resource "google_project_iam_member" "deploy_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.deploy_sa.email}"
}

resource "google_project_iam_member" "deploy_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deploy_sa.email}"
}
