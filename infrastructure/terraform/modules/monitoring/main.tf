terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 6.3" }
  }
}

# Observability dashboards + alerts (blueprint §9.3). Log-based metrics extract
# fields from the structured chat-turn logs (groundedness, safety blocks); alert
# policies watch reliability + quality SLOs. Cheap to create (no standing infra).

variable "project_id" { type = string }
variable "service_name" {
  type    = string
  default = "chat-api"
}
variable "notification_channels" {
  type    = list(string)
  default = []
}

# ── Log-based metrics from the structured "chat turn" logs ───────────────────
resource "google_logging_metric" "groundedness" {
  project = var.project_id
  name    = "fluidra/groundedness"
  filter  = "resource.type=\"cloud_run_revision\" jsonPayload.message=\"chat turn\" jsonPayload.groundedness>=0"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "DISTRIBUTION"
    unit        = "1"
  }
  value_extractor = "EXTRACT(jsonPayload.groundedness)"
  bucket_options {
    linear_buckets {
      num_finite_buckets = 10
      width              = 0.1
      offset             = 0
    }
  }
}

resource "google_logging_metric" "safety_blocks" {
  project = var.project_id
  name    = "fluidra/safety_blocks"
  filter  = "resource.type=\"cloud_run_revision\" jsonPayload.message=\"chat turn\" jsonPayload.blocked=true"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

# ── Alert policies (SLOs) ────────────────────────────────────────────────────
resource "google_monitoring_alert_policy" "p95_latency" {
  project      = var.project_id
  display_name = "${var.service_name} p95 latency > 4s"
  combiner     = "OR"
  conditions {
    display_name = "request p95 latency"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${var.service_name}\" metric.type=\"run.googleapis.com/request_latencies\""
      comparison      = "COMPARISON_GT"
      threshold_value = 4000
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_95"
      }
    }
  }
  notification_channels = var.notification_channels
}

resource "google_monitoring_alert_policy" "error_rate" {
  project      = var.project_id
  display_name = "${var.service_name} 5xx errors"
  combiner     = "OR"
  conditions {
    display_name = "5xx response rate"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${var.service_name}\" metric.type=\"run.googleapis.com/request_count\" metric.label.\"response_code_class\"=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  notification_channels = var.notification_channels
}

# ── Dashboard ────────────────────────────────────────────────────────────────
resource "google_monitoring_dashboard" "main" {
  project = var.project_id
  dashboard_json = jsonencode({
    displayName = "Fluidra Pool Assistant"
    gridLayout = {
      columns = 2
      widgets = [
        {
          title = "Request latency (p95)"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter      = "resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${var.service_name}\" metric.type=\"run.googleapis.com/request_latencies\""
                  aggregation = { alignmentPeriod = "60s", perSeriesAligner = "ALIGN_PERCENTILE_95" }
                }
              }
            }]
          }
        },
        {
          title = "Groundedness (mean)"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter      = "metric.type=\"logging.googleapis.com/user/fluidra/groundedness\""
                  aggregation = { alignmentPeriod = "300s", perSeriesAligner = "ALIGN_DELTA", crossSeriesReducer = "REDUCE_MEAN" }
                }
              }
            }]
          }
        },
        {
          title = "Safety blocks"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter      = "metric.type=\"logging.googleapis.com/user/fluidra/safety_blocks\""
                  aggregation = { alignmentPeriod = "300s", perSeriesAligner = "ALIGN_DELTA" }
                }
              }
            }]
          }
        },
        {
          title = "Request count by status"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter      = "resource.type=\"cloud_run_revision\" resource.label.\"service_name\"=\"${var.service_name}\" metric.type=\"run.googleapis.com/request_count\""
                  aggregation = { alignmentPeriod = "60s", perSeriesAligner = "ALIGN_RATE" }
                }
              }
            }]
          }
        },
      ]
    }
  })
}

output "dashboard_id" {
  value = google_monitoring_dashboard.main.id
}
