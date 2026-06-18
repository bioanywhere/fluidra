terraform {
  required_providers {
    google = { source = "hashicorp/google", version = ">= 6.3" }
  }
}

# Cloud Armor security policy for the external ALB backends: per-IP rate limiting
# (protects the public /v1/chat endpoint from abuse + runaway Vertex cost) and an
# optional OWASP preconfigured WAF. The CRS rules false-positive on free-text
# chat, so they are OFF by default (enable_owasp) — rate limiting is the safe win.

variable "project_id" { type = string }
variable "name" {
  type    = string
  default = "fluidra-armor"
}
variable "rate_limit_count" {
  type        = number
  default     = 120
  description = "Allowed requests per IP per interval before throttling."
}
variable "rate_limit_interval_sec" {
  type    = number
  default = 60
}
variable "ban_duration_sec" {
  type        = number
  default     = 300
  description = "How long an IP stays banned after exceeding the threshold."
}
variable "enable_owasp" {
  type        = bool
  default     = false
  description = "Add OWASP SQLi/XSS preconfigured rules (can false-positive on NL chat)."
}

resource "google_compute_security_policy" "this" {
  project = var.project_id
  name    = var.name

  # OWASP SQLi/XSS (optional; evaluated first so bad payloads are dropped early).
  dynamic "rule" {
    for_each = var.enable_owasp ? [1] : []
    content {
      action      = "deny(403)"
      priority    = 900
      description = "OWASP preconfigured SQLi/XSS"
      match {
        expr {
          expression = "evaluatePreconfiguredExpr('sqli-v33-stable') || evaluatePreconfiguredExpr('xss-v33-stable')"
        }
      }
    }
  }

  # Per-IP rate limit with a temporary ban on sustained abuse.
  rule {
    action      = "rate_based_ban"
    priority    = 1000
    description = "Per-IP rate limit"
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
    rate_limit_options {
      conform_action   = "allow"
      exceed_action    = "deny(429)"
      enforce_on_key   = "IP"
      ban_duration_sec = var.ban_duration_sec
      rate_limit_threshold {
        count        = var.rate_limit_count
        interval_sec = var.rate_limit_interval_sec
      }
    }
  }

  # Default: allow everything else.
  rule {
    action      = "allow"
    priority    = 2147483647
    description = "Default allow"
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
  }
}

output "policy_id" {
  value = google_compute_security_policy.this.id
}
