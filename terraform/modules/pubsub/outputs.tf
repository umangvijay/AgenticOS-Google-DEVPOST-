output "scheduler_topic_id" {
  value = google_pubsub_topic.topics["agentos-scheduler-triggers"].id
}

output "workflow_events_topic_id" {
  value = google_pubsub_topic.topics["agentos-workflow-events"].id
}

output "mcp_validation_topic_id" {
  value = google_pubsub_topic.topics["agentos-mcp-validation"].id
}
