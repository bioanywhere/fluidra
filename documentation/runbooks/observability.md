# Observability runbook (blueprint §9)

What's instrumented, how to turn on each backend, and what the dashboards/alerts
watch.

## Tracing (OpenTelemetry)

Every chat turn is **one trace** (`packages/observability`):

```
chat.turn                         tier, intent, response.type, ai.groundedness
├─ safety.classify                tier, intent, blocked, rule, policy_version
└─ orchestrator.retrieve          rag.chunks, rag.embedder
   orchestrator.generate          ai.model, ai.answer_chars
   orchestrator.verify            ai.groundedness, ai.grounded
```

A hard-blocked or Tier-3 turn has **no `orchestrator.*` spans** — the trace
itself shows the LLM path was never taken.

Exporter is chosen by env (no-op locally, lazy-imported):

```bash
OTEL_TRACES_EXPORTER=none      # default — spans are cheap no-ops
OTEL_TRACES_EXPORTER=console   # print spans (debugging)
OTEL_TRACES_EXPORTER=gcp       # Cloud Trace (needs the `gcp` extra + ADC)
OTEL_TRACES_EXPORTER=otlp      # OTLP collector
```

`init_tracing("<service>")` is called once at startup (chat-api, orchestrator).

## Langfuse (optional, per-trace prompt/response + cost + eval scores)

Env-gated and lazily imported — no-op unless configured:

```bash
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://<your-langfuse>   # self-hosted on Cloud Run (blueprint §2)
```
Install the extra: `uv pip install "observability[langfuse]"`. The orchestrator
records each generation when enabled.

## Dashboards & alerts (Cloud Monitoring)

`infrastructure/terraform/modules/monitoring` (wired into envs/dev) creates:

- **Log-based metrics** from the structured `chat turn` logs:
  `fluidra/groundedness` (distribution) and `fluidra/safety_blocks` (counter).
- **Alert policies**: p95 request latency > 4s, and any 5xx error rate
  (blueprint §9.3). Pass `notification_channels` to route pages.
- **Dashboard** "Fluidra Pool Assistant": latency p95, groundedness mean, safety
  blocks, request count by status.

```bash
# set notification channels (create them once in the console or via gcloud)
terraform apply -var='notification_channels=["projects/<p>/notificationChannels/<id>"]'
```

Structured JSON logs (`observability.setup_logging`) carry tier, intent, blocked,
escalated, groundedness, latency_ms, cost_usd — PII redacted upstream before any
log or trace.

## Verify locally

```bash
uv run pytest packages/observability/tests services/chat-api/tests/test_tracing.py -v
```
Uses an in-memory span exporter to assert the trace shape + attributes offline.
