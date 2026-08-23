# Output a map of environment variables to secret manager version paths
# This can be used directly by the Cloud Run module
output "secret_env_mappings" {
  value = {
    "GEMINI_API_KEY"       = google_secret_manager_secret.app_secrets["gemini_api_key"].id
    "JWT_SECRET"           = google_secret_manager_secret.app_secrets["jwt_secret"].id
    "CORS_ALLOWED_ORIGINS" = google_secret_manager_secret.app_secrets["cors_allowed_origins"].id
  }
}
