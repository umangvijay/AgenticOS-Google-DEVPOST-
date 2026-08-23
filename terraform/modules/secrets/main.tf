# Define the secrets that the application needs
locals {
  app_secrets = [
    "gemini_api_key",
    "jwt_secret",
    "cors_allowed_origins"
  ]
}

resource "google_secret_manager_secret" "app_secrets" {
  for_each  = toset(local.app_secrets)
  secret_id = "agenticos-${each.key}"
  project   = var.project_id
  
  replication {
    auto {}
  }
}

# Grant API Service Account access to read these secrets
resource "google_secret_manager_secret_iam_member" "api_secret_accessor" {
  for_each  = google_secret_manager_secret.app_secrets
  project   = var.project_id
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.api_sa_email}"
}

# Grant Worker Service Account access to read these secrets
resource "google_secret_manager_secret_iam_member" "worker_secret_accessor" {
  for_each  = google_secret_manager_secret.app_secrets
  project   = var.project_id
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.worker_sa_email}"
}
