output "service_url" {
  value = google_cloud_run_v2_service.default.uri
}

output "service_id" {
  value = google_cloud_run_v2_service.default.id
}
