# Dev environment for the Fluidra Pool Assistant (blueprint §11.3).
#
# Composition: enable APIs -> Artifact Registry -> Secret Manager (+ generated
# DB URL) -> Cloud SQL (Postgres/pgvector) -> runtime IAM -> Cloud Run service
# (chat-api) + Cloud Run Jobs (ingestion, eval) -> Workload Identity for CI.

data "google_project" "this" {
  project_id = var.project_id
}

module "services" {
  source     = "../../modules/project-services"
  project_id = var.project_id
}

module "registry" {
  source     = "../../modules/artifact-registry"
  project_id = var.project_id
  region     = var.region
  depends_on = [module.services]
}

resource "random_password" "db" {
  length  = 24
  special = false # avoid URL-encoding issues in the connection string
}

module "sql" {
  source        = "../../modules/cloud-sql"
  project_id    = var.project_id
  region        = var.region
  instance_name = "core"
  db_name       = var.db_name
  db_user       = var.db_user
  db_password   = random_password.db.result
  depends_on    = [module.services]
}

locals {
  conn = module.sql.connection_name
  # Cloud SQL via unix socket mounted at /cloudsql (no VPC connector needed).
  db_url_async = "postgresql+asyncpg://${var.db_user}:${random_password.db.result}@/${var.db_name}?host=/cloudsql/${local.conn}"
  db_url_sync  = "postgresql+psycopg2://${var.db_user}:${random_password.db.result}@/${var.db_name}?host=/cloudsql/${local.conn}"

  chat_api_image    = "${module.registry.repository_path}/chat-api:${var.image_tag}"
  ingestion_image   = "${module.registry.repository_path}/ingestion-worker:${var.image_tag}"
  eval_runner_image = "${module.registry.repository_path}/eval-runner:${var.image_tag}"

  base_env = {
    ENV                   = "dev"
    GCP_PROJECT_ID        = var.project_id
    GCP_REGION            = var.region
    VERTEX_LOCATION       = var.region
    GEMINI_MODEL_FAST     = "gemini-2.5-flash" # only 2.5-flash is served in europe-west1 for this project
    EMBEDDING_MODEL       = "text-embedding-005"
    EMBEDDING_BACKEND     = "vertex"
    LLM_BACKEND           = "vertex"
    SAFETY_POLICY_VERSION = "2025.06.0"
    MAX_TURNS_MEMORY      = "10"
    DB_NAME               = var.db_name
  }

  # Vector backend is config-only: Vertex when enabled, else pgvector. Splat +
  # one() keeps these safe to reference when the module count is 0.
  vector_env = var.enable_vertex_vector_search ? {
    VECTOR_BACKEND           = "vertex"
    VECTOR_INDEX             = one(module.vector_search[*].index_id)
    VECTOR_INDEX_ENDPOINT    = one(module.vector_search[*].index_endpoint_id)
    VECTOR_DEPLOYED_INDEX_ID = one(module.vector_search[*].deployed_index_id)
    VECTOR_DISTANCE_MEASURE  = "COSINE_DISTANCE"
    } : {
    VECTOR_BACKEND = "pgvector"
  }

  app_env = merge(local.base_env, local.vector_env)

  # Ingest the whole manifest corpus; store backend follows the vector flag.
  ingest_args = var.enable_vertex_vector_search ? [
    "--store", "vertex", "--backend", "vertex"
    ] : [
    "--store", "pgvector", "--backend", "vertex"
  ]

  db_secrets = {
    DATABASE_URL      = module.secret_db_url.secret_id
    DATABASE_URL_SYNC = module.secret_db_url_sync.secret_id
  }
}

module "vector_search" {
  count      = var.enable_vertex_vector_search ? 1 : 0
  source     = "../../modules/vector-search"
  project_id = var.project_id
  region     = var.region
  depends_on = [module.services]
}

# ── Secrets (DB URLs generated here; firebase-config is an empty slot) ────────
module "secret_db_url" {
  source      = "../../modules/secret-manager"
  project_id  = var.project_id
  secret_id   = "database-url"
  secret_data = local.db_url_async
  depends_on  = [module.services]
}

module "secret_db_url_sync" {
  source      = "../../modules/secret-manager"
  project_id  = var.project_id
  secret_id   = "database-url-sync"
  secret_data = local.db_url_sync
  depends_on  = [module.services]
}

module "secret_firebase" {
  source     = "../../modules/secret-manager"
  project_id = var.project_id
  secret_id  = "firebase-config" # operator/CI populates the value
  depends_on = [module.services]
}

# ── Runtime service accounts (least privilege) ───────────────────────────────
module "chat_api_sa" {
  source       = "../../modules/iam"
  project_id   = var.project_id
  account_id   = "chat-api"
  display_name = "chat-api runtime"
  roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/aiplatform.user",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ]
}

module "worker_sa" {
  source       = "../../modules/iam"
  project_id   = var.project_id
  account_id   = "kb-worker"
  display_name = "ingestion/eval jobs runtime"
  roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/aiplatform.user",
    "roles/logging.logWriter",
  ]
}

# ── chat-api (public entrypoint) ─────────────────────────────────────────────
module "chat_api" {
  source                = "../../modules/cloud-run-service"
  project_id            = var.project_id
  name                  = "chat-api"
  region                = var.region
  image                 = local.chat_api_image
  service_account_email = module.chat_api_sa.email
  cloudsql_connection   = local.conn
  min_instances         = 0
  max_instances         = 10
  allow_unauthenticated = var.allow_unauthenticated
  env                   = local.app_env
  secrets               = local.db_secrets
  depends_on            = [module.sql, module.secret_db_url, module.secret_db_url_sync]
}

# ── Cloud Run Jobs ───────────────────────────────────────────────────────────
module "ingestion_job" {
  source                = "../../modules/cloud-run-job"
  project_id            = var.project_id
  name                  = "ingestion-worker"
  region                = var.region
  image                 = local.ingestion_image
  service_account_email = module.worker_sa.email
  cloudsql_connection   = local.conn
  command               = ["python", "-m", "ingestion_worker.corpus"]
  args                  = local.ingest_args
  env                   = local.app_env
  secrets               = local.db_secrets
  depends_on            = [module.sql, module.secret_db_url_sync]
}

module "eval_job" {
  source                = "../../modules/cloud-run-job"
  project_id            = var.project_id
  name                  = "eval-runner"
  region                = var.region
  image                 = local.eval_runner_image
  service_account_email = module.worker_sa.email
  command               = ["python", "-m", "eval_runner", "--gate"]
  # Eval runs self-contained (fake backends); switch to vertex for online evals.
  env = { EMBEDDING_BACKEND = "fake", LLM_BACKEND = "fake" }
}

# ── CI deploy identity (GitHub OIDC) ─────────────────────────────────────────
module "wif" {
  source            = "../../modules/workload-identity"
  project_id        = var.project_id
  project_number    = data.google_project.this.number
  github_repository = var.github_repository
  depends_on        = [module.services]
}

module "monitoring" {
  source                = "../../modules/monitoring"
  project_id            = var.project_id
  service_name          = "chat-api"
  notification_channels = var.notification_channels
  depends_on            = [module.services]
}

module "loadbalancer" {
  count        = var.enable_load_balancer ? 1 : 0
  source       = "../../modules/loadbalancer"
  project_id   = var.project_id
  region       = var.region
  service_name = "chat-api"
  depends_on   = [module.chat_api, module.services]
}
