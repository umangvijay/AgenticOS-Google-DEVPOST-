output "api_sa_email" {
  value = google_service_account.api_sa.email
}

output "worker_sa_email" {
  value = google_service_account.worker_sa.email
}

output "scheduler_sa_email" {
  value = google_service_account.scheduler_sa.email
}

output "deploy_sa_email" {
  value = google_service_account.deploy_sa.email
}
