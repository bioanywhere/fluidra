variable "project_id" {
  type        = string
  description = "GCP project id for the dev environment."
}

variable "region" {
  type        = string
  default     = "europe-west1" # EMEA pilot market
  description = "GCP region for all regional resources."
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Container image tag to deploy (set to the git SHA in CI)."
}

variable "db_name" {
  type    = string
  default = "assistant"
}

variable "db_user" {
  type    = string
  default = "app"
}

variable "github_repository" {
  type        = string
  default     = "bioanywhere/fluidra"
  description = "owner/repo allowed to deploy via Workload Identity Federation."
}

variable "allow_unauthenticated" {
  type        = bool
  default     = true # dev: public so you can curl it. Lock down in staging/prod.
  description = "Allow unauthenticated invocation of the Cloud Run service."
}

variable "enable_vertex_vector_search" {
  type        = bool
  default     = false # off by default: a deployed index endpoint is always-on cost
  description = "Provision Vertex AI Vector Search and point chat-api at it (else pgvector)."
}

variable "notification_channels" {
  type        = list(string)
  default     = []
  description = "Cloud Monitoring notification channel IDs for alert policies."
}

variable "enable_load_balancer" {
  type        = bool
  default     = false
  description = "Front chat-api with an external HTTP Application Load Balancer (public IP). Needed when the org disables default run.app URLs."
}

variable "admin_token" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Bearer token for the corpus admin API (/v1/admin/*) and the /admin page. Empty disables admin (fail-closed)."
}

variable "enable_cloud_armor" {
  type        = bool
  default     = false
  description = "Attach a Cloud Armor security policy (per-IP rate limiting + optional WAF) to the load balancer backends."
}

variable "domain" {
  type        = string
  default     = ""
  description = "Custom domain for HTTPS on the load balancer. Empty = HTTP-only on the IP. When set, point the domain's DNS A-record at the LB IP so the managed cert can provision."
}

variable "auth_mode" {
  type        = string
  default     = "stub"
  description = "chat-api end-user auth: 'stub' (dev fixed user) or 'firebase' (verify Firebase ID tokens). Firebase also needs firebase_project_id."
}

variable "firebase_project_id" {
  type        = string
  default     = ""
  description = "Firebase project id used to verify ID tokens (audience). Required when auth_mode=firebase."
}
