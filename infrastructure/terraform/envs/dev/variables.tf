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
