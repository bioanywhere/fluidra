terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 5.0" }
  }
}

# Cloud SQL for PostgreSQL 16. The app creates the `vector` (pgvector) extension
# at runtime; the first SQL user has cloudsqlsuperuser, which is allowed to
# CREATE EXTENSION vector on Cloud SQL.

variable "project_id" { type = string }
variable "region" { type = string }
variable "instance_name" { type = string }
variable "db_name" {
  type    = string
  default = "assistant"
}
variable "db_user" {
  type    = string
  default = "app"
}
variable "db_password" {
  type      = string
  sensitive = true
}
variable "tier" {
  type    = string
  default = "db-custom-1-3840" # 1 vCPU / 3.75 GB — dev sizing
}
variable "deletion_protection" {
  type    = bool
  default = false # dev; set true for staging/prod
}

resource "google_sql_database_instance" "this" {
  project             = var.project_id
  name                = var.instance_name
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = var.deletion_protection

  settings {
    tier              = var.tier
    edition           = "ENTERPRISE" # ENTERPRISE_PLUS rejects db-custom-* tiers
    availability_type = "ZONAL"      # dev; REGIONAL for prod HA
    disk_autoresize   = true
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
    ip_configuration {
      ipv4_enabled = true # dev convenience; prefer private IP in prod
    }
  }
}

resource "google_sql_database" "this" {
  project  = var.project_id
  name     = var.db_name
  instance = google_sql_database_instance.this.name
}

resource "google_sql_user" "this" {
  project  = var.project_id
  name     = var.db_user
  instance = google_sql_database_instance.this.name
  password = var.db_password
}

output "connection_name" {
  value = google_sql_database_instance.this.connection_name
}
output "instance_name" {
  value = google_sql_database_instance.this.name
}
