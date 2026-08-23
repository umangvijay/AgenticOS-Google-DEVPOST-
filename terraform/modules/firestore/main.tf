resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = var.database
  location_id = var.location_id
  type        = "FIRESTORE_NATIVE"
}

# Provision a single-field Vector Index for the memory collection
resource "google_firestore_index" "memory_vector_index" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "memory"

  fields {
    field_path = "embedding"
    # For vector search, we define the vector configuration
    vector_config {
      dimension = 768 # text-embedding-004 output dimension
      flat {} # Uses exact nearest neighbors (FLAT)
    }
  }

  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }

  depends_on = [
    google_firestore_database.default
  ]
}

# Provision standard indexes if needed, e.g., for task queries
resource "google_firestore_index" "task_status_index" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "tasks"

  fields {
    field_path = "run_id"
    order      = "ASCENDING"
  }
  
  fields {
    field_path = "status"
    order      = "ASCENDING"
  }

  depends_on = [
    google_firestore_database.default
  ]
}
