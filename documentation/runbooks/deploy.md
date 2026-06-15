# Deploy runbook — dev environment (Cloud Run + Terraform)

Provisions and deploys the Fluidra Pool Assistant to a **dev** GCP project:
Cloud Run (chat-api) + Cloud SQL (Postgres/pgvector) + Secret Manager +
Artifact Registry + Workload Identity for CI. Blueprint §11.

> **Scope:** this repo contains the complete IaC. Running it requires a GCP
> project, billing, and the `gcloud`/`terraform` CLIs. Nothing here has been
> applied — the steps below are the first apply.

---

## 0. Prerequisites (one-time)

```bash
# Tools
brew install terraform google-cloud-sdk     # or your OS equivalent

# A project with billing enabled
gcloud projects create fluidra-pool-asst-dev          # or use an existing one
gcloud config set project fluidra-pool-asst-dev
gcloud auth login
gcloud auth application-default login

# Remote state bucket (versioned)
gsutil mb -l europe-west1 gs://fluidra-pool-asst-tfstate
gsutil versioning set on gs://fluidra-pool-asst-tfstate
```

The Terraform `project-services` module enables the required APIs on first apply
(run, sqladmin, secretmanager, artifactregistry, aiplatform, iam, …).

---

## 1. First apply (creates infra, but images don't exist yet)

Apply everything **except** the Cloud Run resources first, so the registry +
Cloud SQL + secrets exist and we have somewhere to push images:

```bash
cd infrastructure/terraform/envs/dev
cp terraform.tfvars.example terraform.tfvars   # edit project_id etc.

terraform init -backend-config="bucket=fluidra-pool-asst-tfstate"

# Stand up registry + DB + secrets + IAM first
terraform apply \
  -target=module.registry -target=module.sql \
  -target=module.secret_db_url -target=module.secret_db_url_sync \
  -target=module.chat_api_sa -target=module.worker_sa
```

---

## 2. Build & push images

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=europe-west1
REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/svc"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

docker build -f infrastructure/docker/python.Dockerfile \
  --build-arg SERVICE=chat-api --build-arg APP_MODULE=chat_api.main:app \
  -t "${REPO}/chat-api:latest" .
docker push "${REPO}/chat-api:latest"

docker build -f infrastructure/docker/python.Dockerfile \
  --build-arg SERVICE=ingestion-worker -t "${REPO}/ingestion-worker:latest" .
docker push "${REPO}/ingestion-worker:latest"

docker build -f infrastructure/docker/python.Dockerfile \
  --build-arg SERVICE=eval-runner -t "${REPO}/eval-runner:latest" .
docker push "${REPO}/eval-runner:latest"
```

---

## 3. Full apply (Cloud Run service + jobs + WIF)

```bash
cd infrastructure/terraform/envs/dev
terraform apply        # creates chat-api service, jobs, workload identity

terraform output chat_api_url     # the public URL
```

---

## 4. Ingest the manual + smoke test

```bash
# Run the ingestion job once to populate pgvector
gcloud run jobs execute ingestion-worker --region europe-west1 --wait

# Smoke test
./scripts/smoke.sh "$(terraform -chdir=infrastructure/terraform/envs/dev output -raw chat_api_url)"

# Try the demo turn
curl -s -X POST "$(terraform -chdir=infrastructure/terraform/envs/dev output -raw chat_api_url)/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"11111111-1111-1111-1111-111111111111","message":"my salt system shows code 125"}'
```

---

## 5. Wire CI deploys (GitHub OIDC)

From the apply outputs, set in GitHub → Settings → Secrets and variables → Actions:

| Kind | Name | Value |
|------|------|-------|
| secret | `WIF_PROVIDER` | `terraform output -raw wif_provider` |
| secret | `DEPLOY_SA` | `terraform output -raw deployer_sa_email` |
| variable | `GCP_PROJECT_ID` | your project id |
| variable | `GCP_REGION` | `europe-west1` |
| variable | `TF_STATE_BUCKET` | `fluidra-pool-asst-tfstate` |

Then a tag push deploys:

```bash
git tag v0.1.0 && git push origin v0.1.0   # triggers .github/workflows/deploy.yml
```

---

## Rollback (blueprint §11.5)

```bash
# App: instant revision rollback
gcloud run services update-traffic chat-api --region europe-west1 \
  --to-revisions <PREVIOUS_REVISION>=100

# Kill switch (no deploy needed): set KILL_SWITCH_FLAG off via env/secret update
```

---

## Notes & deviations (MVP)

- **Runtime base is `python:3.12-slim`, not distroless** — the current distroless
  Python base is 3.11; this project requires 3.12. Distroless is a Target-state
  hardening once a 3.12 base exists.
- **Cloud SQL public IP + unix-socket connection** for dev simplicity (no VPC
  connector). Prod should use private IP + VPC, `REGIONAL` availability, and
  `deletion_protection = true`.
- **`allow_unauthenticated = true`** in dev so you can curl the service. Prod
  fronts Cloud Run with the load balancer + IAP (`INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER`).
- **Vector store stays pgvector** here; swapping to Vertex AI Vector Search is the
  next widening step (the retrieval interface is already abstract).
