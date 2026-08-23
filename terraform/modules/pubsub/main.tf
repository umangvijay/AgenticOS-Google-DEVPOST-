locals {
  topics = [
    "agentos-workflow-events",
    "agentos-scheduler-triggers",
    "agentos-mcp-validation"
  ]
}

resource "google_pubsub_topic" "topics" {
  for_each = toset(local.topics)
  name     = each.key
  project  = var.project_id
}

# Create Push Subscriptions pointing to the Worker Cloud Run Service
resource "google_pubsub_subscription" "worker_push_subs" {
  for_each = toset(local.topics)
  name     = "${each.key}-worker-sub"
  project  = var.project_id
  topic    = google_pubsub_topic.topics[each.key].name

  ack_deadline_seconds = 600 # 10 minutes

  push_config {
    push_endpoint = "${var.worker_endpoint}/pubsub/push"

    # Authenticate the push request with the worker's service account
    oidc_token {
      service_account_email = var.worker_sa_email
    }
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}
