terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
  }
}

# A runtime service account + its least-privilege project role bindings.

variable "project_id" { type = string }
variable "account_id" { type = string }
variable "display_name" {
  type    = string
  default = ""
}
variable "roles" {
  type    = list(string)
  default = []
}

resource "google_service_account" "this" {
  project      = var.project_id
  account_id   = var.account_id
  display_name = var.display_name != "" ? var.display_name : var.account_id
}

resource "google_project_iam_member" "roles" {
  for_each = toset(var.roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.this.email}"
}

output "email" {
  value = google_service_account.this.email
}
output "member" {
  value = "serviceAccount:${google_service_account.this.email}"
}
