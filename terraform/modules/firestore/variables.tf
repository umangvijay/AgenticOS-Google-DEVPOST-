variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "database" {
  type        = string
  description = "Firestore Database ID"
  default     = "(default)"
}

variable "location_id" {
  type        = string
  description = "Location for Firestore database (e.g. nam5, us-central1)"
  default     = "nam5"
}
