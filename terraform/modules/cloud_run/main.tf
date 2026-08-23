resource "google_cloud_run_v2_service" "default" {
  name     = var.service_name
  location = var.region
  project  = var.project_id
  
  template {
    service_account = var.service_account
    timeout         = "${var.timeout_seconds}s"
    
    containers {
      image = var.image
      
      dynamic "env" {
        for_each = var.environment_vars
        content {
          name  = env.key
          value = env.value
        }
      }
      
      dynamic "env" {
        for_each = var.secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = element(split("/", env.value), 3) # Extracts secret name from full ID
              version = "latest" # or specific version if needed
            }
          }
        }
      }
    }
    
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    max_instance_request_concurrency = var.concurrency
  }
}

# IAM Policies for invocation
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

data "google_iam_policy" "auth" {
  binding {
    role = "roles/run.invoker"
    members = [for email in var.invoker_sa_emails : "serviceAccount:${email}"]
  }
}

resource "google_cloud_run_v2_service_iam_policy" "policy" {
  project     = google_cloud_run_v2_service.default.project
  location    = google_cloud_run_v2_service.default.location
  name        = google_cloud_run_v2_service.default.name
  policy_data = var.is_public ? data.google_iam_policy.noauth.policy_data : (length(var.invoker_sa_emails) > 0 ? data.google_iam_policy.auth.policy_data : null)
}
