output "api_service_url" {
  value = module.cloud_run_api.service_url
}

output "worker_service_url" {
  value = module.cloud_run_worker.service_url
}

output "pubsub_workflow_events_topic" {
  value = module.pubsub.workflow_events_topic_id
}

output "scheduler_topic" {
  value = module.pubsub.scheduler_topic_id
}
