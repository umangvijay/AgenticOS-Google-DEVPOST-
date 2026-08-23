terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "agenticos-tfstate-dev" # This needs to exist or be created outside this config
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Module Invocations ---

# IAM
module "iam" {
  source     = "../../modules/iam"
  project_id = var.project_id
}

# Secrets
module "secrets" {
  source     = "../../modules/secrets"
  project_id = var.project_id
  api_sa_email = module.iam.api_sa_email
  worker_sa_email = module.iam.worker_sa_email
}

# Firestore
module "firestore" {
  source      = "../../modules/firestore"
  project_id  = var.project_id
  database    = "(default)"
  location_id = "nam5"
}

# Pub/Sub
module "pubsub" {
  source            = "../../modules/pubsub"
  project_id        = var.project_id
  worker_endpoint   = module.cloud_run_worker.service_url
  worker_sa_email   = module.iam.worker_sa_email
}

# Cloud Run Worker
module "cloud_run_worker" {
  source              = "../../modules/cloud_run"
  project_id          = var.project_id
  region              = var.region
  service_name        = "agenticos-worker"
  image               = var.worker_image
  service_account     = module.iam.worker_sa_email
  min_instances       = 1
  max_instances       = 10
  timeout_seconds     = 3600 # 1 hour for long running tasks
  concurrency         = 10
  environment_vars    = merge(var.shared_env_vars, {
    "SERVICE_TYPE" = "WORKER"
  })
  secrets             = module.secrets.secret_env_mappings
  invoker_sa_emails   = [module.iam.worker_sa_email] # PubSub push uses this SA
  is_public           = false
}

# Cloud Run API
module "cloud_run_api" {
  source              = "../../modules/cloud_run"
  project_id          = var.project_id
  region              = var.region
  service_name        = "agenticos-api"
  image               = var.api_image
  service_account     = module.iam.api_sa_email
  min_instances       = 0
  max_instances       = 50
  timeout_seconds     = 300
  concurrency         = 80
  environment_vars    = merge(var.shared_env_vars, {
    "SERVICE_TYPE" = "API"
  })
  secrets             = module.secrets.secret_env_mappings
  is_public           = true
}

# Cloud Scheduler
module "scheduler" {
  source             = "../../modules/scheduler"
  project_id         = var.project_id
  region             = var.region
  pubsub_topic_id    = module.pubsub.scheduler_topic_id
  scheduler_sa_email = module.iam.scheduler_sa_email
}

# Artifact Registry
module "artifact_registry" {
  source     = "../../modules/artifact_registry"
  project_id = var.project_id
  region     = var.region
  deploy_sa_email = module.iam.deploy_sa_email
}
