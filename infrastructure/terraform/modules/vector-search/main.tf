terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 6.3" }
  }
}

# Vertex AI Vector Search: a streaming index + a public endpoint with the index
# deployed. STREAM_UPDATE lets the ingestion worker upsert_datapoints in real
# time. Dimensions must match the embedding model (text-embedding-005 = 768).
#
# NOTE: a deployed index endpoint runs dedicated replicas (always-on cost). This
# module is disabled by default in the dev env (see enable_vertex_vector_search).

variable "project_id" { type = string }
variable "region" { type = string }
variable "dim" {
  type    = number
  default = 768 # text-embedding-005
}
variable "distance_measure" {
  type    = string
  default = "COSINE_DISTANCE"
}
variable "deployed_index_id" {
  type    = string
  default = "manuals_v1"
}
variable "min_replicas" {
  type    = number
  default = 1
}
variable "max_replicas" {
  type    = number
  default = 1
}

resource "google_vertex_ai_index" "this" {
  project      = var.project_id
  region       = var.region
  display_name = "fluidra-manuals"
  description  = "Manual chunk embeddings for the Pool Assistant."

  metadata {
    config {
      dimensions                  = var.dim
      approximate_neighbors_count = 150
      distance_measure_type       = var.distance_measure
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 500
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }

  index_update_method = "STREAM_UPDATE"
}

resource "google_vertex_ai_index_endpoint" "this" {
  project                 = var.project_id
  region                  = var.region
  display_name            = "fluidra-manuals-endpoint"
  public_endpoint_enabled = true
}

resource "google_vertex_ai_index_endpoint_deployed_index" "this" {
  index_endpoint    = google_vertex_ai_index_endpoint.this.id
  index             = google_vertex_ai_index.this.id
  deployed_index_id = var.deployed_index_id
  display_name      = "manuals deployed"

  dedicated_resources {
    machine_spec {
      machine_type = "e2-standard-2"
    }
    min_replica_count = var.min_replicas
    max_replica_count = var.max_replicas
  }
}

output "index_id" {
  value = google_vertex_ai_index.this.id
}
output "index_endpoint_id" {
  value = google_vertex_ai_index_endpoint.this.id
}
output "deployed_index_id" {
  value = google_vertex_ai_index_endpoint_deployed_index.this.deployed_index_id
}
