terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
  }
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "repository_id" {
  type    = string
  default = "svc"
}

resource "google_artifact_registry_repository" "this" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
  description   = "Container images for the Fluidra Pool Assistant services."
}

# europe-west1-docker.pkg.dev/<project>/<repo>
output "registry_host" {
  value = "${var.region}-docker.pkg.dev"
}
output "repository_path" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.this.repository_id}"
}
