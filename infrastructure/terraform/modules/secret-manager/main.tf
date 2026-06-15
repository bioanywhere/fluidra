terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
  }
}

# A Secret Manager secret. If `secret_data` is set, an initial version is created
# (used for Terraform-generated values like the DB connection URL). Otherwise the
# secret is an empty slot for an operator/CI to populate (blueprint §4.2).

variable "project_id" { type = string }
variable "secret_id" { type = string }
variable "secret_data" {
  type      = string
  default   = null
  sensitive = true
}

resource "google_secret_manager_secret" "this" {
  project   = var.project_id
  secret_id = var.secret_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "this" {
  count       = var.secret_data == null ? 0 : 1
  secret      = google_secret_manager_secret.this.id
  secret_data = var.secret_data
}

output "secret_id" {
  value = google_secret_manager_secret.this.secret_id
}
output "secret_name" {
  value = google_secret_manager_secret.this.name
}
