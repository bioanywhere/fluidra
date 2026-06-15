terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
  }
}

# Cloud Run Job for batch work (ingestion, evals; blueprint §1.3). Same image
# shape as services, but with an explicit command/args and no port.

variable "project_id" { type = string }
variable "name" { type = string }
variable "region" { type = string }
variable "image" { type = string }
variable "service_account_email" { type = string }
variable "command" {
  type    = list(string)
  default = []
}
variable "args" {
  type    = list(string)
  default = []
}
variable "env" {
  type    = map(string)
  default = {}
}
variable "secrets" {
  type    = map(string)
  default = {}
}
variable "cloudsql_connection" {
  type    = string
  default = ""
}

resource "google_cloud_run_v2_job" "this" {
  project             = var.project_id
  name                = var.name
  location            = var.region
  deletion_protection = false

  template {
    template {
      service_account = var.service_account_email

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
        image   = var.image
        command = length(var.command) > 0 ? var.command : null
        args    = length(var.args) > 0 ? var.args : null

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
  }
}

output "job_name" {
  value = google_cloud_run_v2_job.this.name
}
