# Example default scheduler job that triggers a system heartbeat or cleanup
resource "google_cloud_scheduler_job" "default_heartbeat" {
  name             = "agentos-system-heartbeat"
  description      = "Default heartbeat for AgenticOS"
  schedule         = "0 * * * *" # Every hour
  time_zone        = "UTC"
  project          = var.project_id
  region           = var.region

  pubsub_target {
    topic_name = var.pubsub_topic_id
    data       = base64encode(jsonencode({ "action": "heartbeat", "source": "scheduler" }))
  }
}
