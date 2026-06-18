# Fast, doc-only layer on top of the current web image. Replaces the served
# blueprint markdown without a full pnpm install + next build (seconds, and it
# avoids the npm-registry network path). Use for documentation-only updates:
#
#   docker build -f infrastructure/docker/web-docpatch.Dockerfile \
#     -t europe-west1-docker.pkg.dev/fluidra-499509/svc/web:latest .
#
# The next full web build (web.Dockerfile) regenerates this from the repo root,
# so there is no drift — the root markdown stays the single source of truth.
FROM europe-west1-docker.pkg.dev/fluidra-499509/svc/web:latest
COPY Fluidra_Implementation_Blueprint.md /app/apps/web/public/Fluidra_Implementation_Blueprint.md
