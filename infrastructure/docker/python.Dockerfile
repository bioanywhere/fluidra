# Multi-stage build for any Python service in the uv workspace (blueprint §11.2).
#
#   docker build -f infrastructure/docker/python.Dockerfile \
#     --build-arg SERVICE=chat-api \
#     --build-arg APP_MODULE=chat_api.main:app \
#     -t chat-api .
#
# SERVICE    = uv workspace package name (chat-api, orchestrator, ingestion-worker, …)
# APP_MODULE = uvicorn target for HTTP services (ignored by Cloud Run Jobs, which
#              override the container command).
#
# NOTE: runtime is python:3.12-slim, not distroless — the current distroless
# python base is 3.11 and this project requires 3.12. Distroless is a
# Target-state hardening once a 3.12 base is available.

FROM python:3.12-slim AS build
RUN pip install --no-cache-dir uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Copy the whole workspace (the .dockerignore keeps it lean) so uv can resolve
# the workspace members the target service depends on.
COPY . .

ARG SERVICE=chat-api
# Install ONLY the target service + its (workspace) dependencies into /app/.venv.
RUN uv sync --frozen --no-dev --package "${SERVICE}"

# ---- runtime ----
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=build /app /app

ARG APP_MODULE=chat_api.main:app
ENV PATH="/app/.venv/bin:${PATH}" \
    APP_MODULE="${APP_MODULE}" \
    PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
# Cloud Run sets $PORT; uvicorn binds it. Jobs override this command via Terraform.
CMD ["sh", "-c", "uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT}"]
