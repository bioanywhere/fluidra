terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 6.3" }
  }
}

# Global external Application Load Balancer fronting two Cloud Run services
# (serverless NEGs): the Next.js web app at "/" and chat-api for the API paths.
# A single public IP works even when the org disables default run.app URLs, and
# same-origin routing means the browser needs no CORS for the hosted app.

variable "project_id" { type = string }
variable "region" { type = string }
variable "api_service_name" { type = string }
variable "web_service_name" { type = string }
variable "name" {
  type    = string
  default = "chat-api-lb"
}

# ── serverless NEGs ──────────────────────────────────────────────────────────
resource "google_compute_region_network_endpoint_group" "api" {
  project               = var.project_id
  name                  = "${var.name}-api-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run { service = var.api_service_name }
}

resource "google_compute_region_network_endpoint_group" "web" {
  project               = var.project_id
  name                  = "${var.name}-web-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run { service = var.web_service_name }
}

# ── backend services ─────────────────────────────────────────────────────────
resource "google_compute_backend_service" "api" {
  project               = var.project_id
  name                  = "${var.name}-api-bes"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  backend { group = google_compute_region_network_endpoint_group.api.id }
}

resource "google_compute_backend_service" "web" {
  project               = var.project_id
  name                  = "${var.name}-web-bes"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  backend { group = google_compute_region_network_endpoint_group.web.id }
}

# ── routing: "/" -> web, API paths -> chat-api ───────────────────────────────
resource "google_compute_url_map" "this" {
  project         = var.project_id
  name            = "${var.name}-um"
  default_service = google_compute_backend_service.web.id

  host_rule {
    hosts        = ["*"]
    path_matcher = "main"
  }
  path_matcher {
    name            = "main"
    default_service = google_compute_backend_service.web.id
    path_rule {
      paths   = ["/v1", "/v1/*", "/healthz", "/docs", "/openapi.json", "/redoc"]
      service = google_compute_backend_service.api.id
    }
  }
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
