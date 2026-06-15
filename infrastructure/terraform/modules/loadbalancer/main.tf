terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 6.3" }
  }
}

# Global external Application Load Balancer -> Cloud Run (serverless NEG).
# Provides a stable public IP that works even when the org disables default
# run.app URLs. This is also the blueprint's prod ingress (add Cloud Armor +
# HTTPS/managed cert there). HTTP-only here for a dev smoke test (no domain).

variable "project_id" { type = string }
variable "region" { type = string }
variable "service_name" { type = string }
variable "name" {
  type    = string
  default = "chat-api-lb"
}

resource "google_compute_region_network_endpoint_group" "neg" {
  project               = var.project_id
  name                  = "${var.name}-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = var.service_name
  }
}

resource "google_compute_backend_service" "this" {
  project               = var.project_id
  name                  = "${var.name}-bes"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  backend {
    group = google_compute_region_network_endpoint_group.neg.id
  }
}

resource "google_compute_url_map" "this" {
  project         = var.project_id
  name            = "${var.name}-um"
  default_service = google_compute_backend_service.this.id
}

resource "google_compute_target_http_proxy" "this" {
  project = var.project_id
  name    = "${var.name}-proxy"
  url_map = google_compute_url_map.this.id
}

resource "google_compute_global_address" "this" {
  project = var.project_id
  name    = "${var.name}-ip"
}

resource "google_compute_global_forwarding_rule" "this" {
  project               = var.project_id
  name                  = "${var.name}-fr"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.this.id
  ip_address            = google_compute_global_address.this.id
}

output "ip" {
  value = google_compute_global_address.this.address
}
