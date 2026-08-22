variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "database" {
  type        = string
  description = "Firestore Database ID"
  default     = "(default)"
}

# Provision a single-field Vector Index for the memory collection
# Note: Requires google provider version that supports vector_config for Firestore (v5.x+)
resource "google_firestore_index" "memory_vector_index" {
  project    = var.project_id
  database   = var.database
  collection = "memory"

  fields {
    field_path = "embedding"
    # For vector search, we define the vector configuration
    vector_config {
      dimension = 768 # text-embedding-004 output dimension
      flat {} # Uses exact nearest neighbors (FLAT)
    }
  }
}
