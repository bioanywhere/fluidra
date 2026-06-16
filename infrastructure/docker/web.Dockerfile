# Next.js (apps/web) standalone image for Cloud Run.
#
#   docker build -f infrastructure/docker/web.Dockerfile \
#     --build-arg NEXT_PUBLIC_API_BASE_URL="" -t web .
#
# NEXT_PUBLIC_API_BASE_URL is inlined at build time. Empty "" => the browser
# fetches /v1/chat same-origin (served behind the same load balancer as the API).

FROM node:20-slim AS build
RUN corepack enable
WORKDIR /app
COPY . .
# root .npmrc has shamefully-hoist=true so `next` resolves in the container.
RUN pnpm install --frozen-lockfile
ARG NEXT_PUBLIC_API_BASE_URL=""
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
# exec resolves the (hoisted) next binary directly, bypassing the workspace
# package's .bin shim which doesn't resolve in this container.
RUN pnpm --filter web exec next build

# ---- runtime ----
FROM node:20-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production PORT=8080
# Next standalone output (monorepo layout: apps/web/server.js + node_modules)
COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /app/apps/web/public ./apps/web/public
EXPOSE 8080
CMD ["node", "apps/web/server.js"]
