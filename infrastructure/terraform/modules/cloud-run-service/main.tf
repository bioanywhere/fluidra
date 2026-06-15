terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
  }
}

# Stateless Cloud Run service (blueprint §11.3). Plain env vars + secret-backed
# env vars (by reference, resolved at boot) + an optional Cloud SQL connection
# mounted as a unix socket at /cloudsql.

variable "project_id" { type = string }
variable "name" { type = string }
variable "region" { type = string }
variable "image" { type = string }
variable "service_account_email" { type = string }

variable "env" {
  type    = map(string)
  default = {}
}
# Map of ENV_VAR_NAME => secret_id (Secret Manager, same project).
variable "secrets" {
  type    = map(string)
  default = {}
}
variable "cloudsql_connection" {
  type    = string
  default = "" # "project:region:instance"; empty = no Cloud SQL volume
}
variable "min_instances" {
  type    = number
  default = 0
}
variable "max_instances" {
  type    = number
  default = 10
}
variable "ingress" {
  type    = string
  default = "INGRESS_TRAFFIC_ALL" # dev; prod uses INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER
}
variable "allow_unauthenticated" {
  type    = bool
  default = false
}

resource "google_cloud_run_v2_service" "this" {
  project             = var.project_id
  name                = var.name
  location            = var.region
  ingress             = var.ingress
  deletion_protection = false

  template {
    service_account = var.service_account_email
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    dynamic "volumes" {
      for_each = var.cloudsql_connection == "" ? [] : [var.cloudsql_connection]
      content {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [volumes.value]
        }
      }
    }

    containers {
      image = var.image
      ports {
        container_port = 8080
      }
      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }

      dynamic "env" {
        for_each = var.env
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
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      dynamic "volume_mounts" {
        for_each = var.cloudsql_connection == "" ? [] : [1]
        content {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "invoker" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "uri" {
  value = google_cloud_run_v2_service.this.uri
}
