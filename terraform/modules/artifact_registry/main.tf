resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "agenticos-repo"
  description   = "Docker repository for AgenticOS images"
  format        = "DOCKER"
  project       = var.project_id
}

resource "google_artifact_registry_repository_iam_member" "deploy_writer" {
  project    = google_artifact_registry_repository.repo.project
  location   = google_artifact_registry_repository.repo.location
  repository = google_artifact_registry_repository.repo.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${var.deploy_sa_email}"
}

# (Optional) Enable vulnerability scanning using Container Analysis API if not already enabled at project level
# Usually done via Project services, but we can leave a note here.
