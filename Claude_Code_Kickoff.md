# Claude Code Kickoff — Fluidra Pool Assistant

**How to use this file:**
1. Create an empty folder: `mkdir fluidra-pool-assistant && cd fluidra-pool-assistant`
2. Put `Fluidra_Implementation_Blueprint.md` in that folder (it's the spec).
3. Start Claude Code in the folder: `claude`
4. Paste the **KICKOFF PROMPT** below as your first message.
5. After it finishes Milestone 1, paste the next milestone prompt. Work milestone by milestone — don't ask for everything at once.

---

## KICKOFF PROMPT (paste this first)

```
You are building the Fluidra Pool Assistant, a Gemini-powered conversational
assistant for residential pool owners. The complete specification is in
./Fluidra_Implementation_Blueprint.md — read it fully before writing any code.
It is the source of truth for architecture, tech stack, repo structure, schema,
the safety model, and the deployment approach.

CONTEXT YOU MUST RESPECT:
- The brief: production-ready patterns, but realistic for a 3-person team in 90 days.
  Build the "🟢 MVP (90 days)" tier from the blueprint, NOT the "🔵 Target state" tier.
- Stack: Python 3.12 + FastAPI, GCP-native (Cloud Run, Vertex AI, Vertex Vector
  Search), Postgres, Terraform, Turborepo monorepo, uv for Python.
- The single most important design rule: SAFETY IS ENFORCED BEFORE GENERATION.
  A deterministic classifier runs before any LLM call. Chemical-mixing queries are
  hard-blocked and must NEVER reach the model. Physical-risk queries route to human
  escalation. Read §5.5 and §6 of the blueprint carefully — this is non-negotiable.

WE ARE BUILDING THE VERTICAL SLICE FIRST — the Day-0-to-30 wedge:
a pool owner asks about an equipment fault code, and the assistant returns a
grounded, cited answer from one ingested manual — end to end, running locally,
with the safety gateway in front. We prove the architecture before widening scope.

HOW I WANT YOU TO WORK:
- Work in the MILESTONES below, one at a time. Stop after each milestone, summarize
  what you built and how to run it, and wait for me to say "continue" before the next.
- Write real, runnable code with tests — not stubs. Every milestone must run locally.
- Follow the blueprint's repo structure exactly. Use uv workspaces and Turborepo.
- Twelve-Factor: config in env, no secrets in code, structured logging.
- After each milestone, give me the exact commands to verify it works.
- If the blueprint is ambiguous, make a sensible MVP choice, state it in one line,
  and keep moving. Don't ask me to clarify small things.

MILESTONE 1 — Repository skeleton + local dev environment
Build:
- The Turborepo monorepo structure from blueprint §3 (only the folders we need now:
  services/chat-api, services/safety-gateway, services/orchestrator, packages/
  shared-types, packages/safety-policy, packages/chemistry-tables, infrastructure/docker).
- uv workspace (pyproject.toml) + Turborepo (turbo.json) + a Makefile with
  `bootstrap`, `dev`, `test` targets exactly as in blueprint §4.4.
- docker compose for local Postgres + Redis (blueprint §4.4).
- A health-check FastAPI app in chat-api that boots, connects to Postgres, and
  returns {"status":"ok"} on GET /healthz.
- The Alembic setup + the initial migration from blueprint §5.3 (all tables).
- A README in /documentation/onboarding with the day-one setup steps.

Verify for me: `make bootstrap`, then `make dev`, then `curl localhost:8080/healthz`
returns ok, and the DB has the tables. Then STOP and wait for "continue".
```

---

## MILESTONE 2 (paste after M1 verifies)

```
continue

MILESTONE 2 — The safety gateway (the heart of the system)
This is the most important milestone. Build services/safety-gateway exactly to
blueprint §5.5:
- The deterministic classifier: PII redaction, the MIXING_PATTERNS hard-block,
  the T3 physical-risk patterns, and a simple intent router (for now, a keyword/
  zero-shot stub for "dosing" vs "fault_code" vs "maintenance" — we'll upgrade later).
- The Tier enum and Decision dataclass.
- packages/safety-policy: move the patterns, block lists, and disclaimer strings
  here as a VERSIONED package (they change under legal review, per the blueprint).
- A comprehensive safety test suite in tests/safety/ — the mixing-block test from
  blueprint §10, PLUS paraphrases, leetspeak, and a few Spanish-language variants.
  The hard gate: 100% of mixing attempts blocked, and they must never be routed to
  the orchestrator. Make this test impossible to pass accidentally.

Verify: `uv run pytest tests/safety -v` — all green, with the mixing-block test
proving the LLM path is never reached. Then STOP.
```

---

## MILESTONE 3 (paste after M2 verifies)

```
continue

MILESTONE 3 — Knowledge ingestion (one manual) + retrieval
Build a minimal version of services/ingestion-worker (blueprint §8):
- Ingest ONE real manual we provide (start with a public Jandy or Polaris PDF —
  e.g. the AquaPure or Alpha iQ manual). Parse it, chunk it structure-aware with
  metadata {doc_id, brand, model, section, url} per blueprint §6.2.
- For LOCAL dev, use Postgres + pgvector as the vector store (blueprint lists it as
  the small-scale fallback) so we don't need live Vertex Vector Search yet. Keep the
  retrieval interface abstract so we can swap in Vertex Vector Search later with no
  call-site changes.
- Embeddings: wire Vertex AI text-embedding-005 via Application Default Credentials,
  with a local fake-embedding fallback so the pipeline runs offline in tests.
- A retrieval function: top-k=6, metadata pre-filter, hybrid (dense + keyword on
  fault-code strings like "125", "FAULT-HIGH LIMIT").

Verify: an ingestion command that loads the manual and reports chunk count, plus a
retrieval test that returns the correct manual section for a known fault code. STOP.
```

---

## MILESTONE 4 (paste after M3 verifies)

```
continue

MILESTONE 4 — Orchestrator: grounded, cited Gemini answers
Build services/orchestrator per blueprint §6.1:
- The LangGraph graph: retrieve → generate → verify → (fallback). Real code.
- Gemini via Vertex AI (gemini-2.0-flash for now), with the system persona from a
  versioned file in packages/prompts.
- Citation binding (§6.5): the response includes structured citations
  {doc_id, section, url}.
- The groundedness verify node (§6.1): if groundedness < 0.8, route to fallback
  (graceful escalation message) instead of answering. No hallucinated answers.
- A local fake-LLM mode for tests so CI runs without hitting Vertex.

Verify: a test where "my salt system shows code 125" returns a grounded answer with
a citation to the ingested manual, and an out-of-scope question routes to fallback. STOP.
```

---

## MILESTONE 5 (paste after M4 verifies)

```
continue

MILESTONE 5 — Wire it end to end + the eval gate
- chat-api POST /v1/chat (blueprint §5.4): auth stub for local, load memory window
  from Postgres, call safety-gateway, then route: T1→orchestrator, T2→dosing stub,
  T3→escalation stub. Persist the turn (redacted) with tier, latency, cost.
- Implement the dosing-service deterministic calculator (blueprint §6 / chemistry-
  tables package) for the T2 path — real math from validated tables, never the LLM.
- A minimal eval-runner (blueprint §6.6): a golden set of ~20 questions (fault codes,
  safety, one dosing) with pass thresholds, runnable as `uv run python -m eval_runner`.
- Wire the eval gate + safety suite into a GitHub Actions workflow (blueprint §11.4)
  that blocks merge on regression.

Verify: full local flow — start the stack, POST the three demo questions from the
presentation (code 125 → cited answer; "how much chlorine" → dosing card; "burning
smell" → escalation), and run the eval suite green. This completes the vertical slice.
```

---

## After the slice

Once Milestone 5 runs end to end, you have a working, safe, grounded assistant
proving the whole architecture. From there, widen in this order (each is a session):
1. Terraform + Cloud Run deploy to a dev GCP project (blueprint §11.3).
2. Swap pgvector → Vertex AI Vector Search (interface already abstract).
3. The Next.js chat frontend (blueprint §7) with the three tier-aware message types.
4. Ingest the full priority-manual set; expand the golden sets.
5. Observability: OpenTelemetry + Langfuse + the dashboards (blueprint §9).

## Tips for working with Claude Code on this
- Keep the blueprint in the repo root so it's always in context.
- One milestone per session keeps the context window focused and the work reviewable.
- Commit after every green milestone — `git commit -m "M2: safety gateway"`.
- When you add the real Gemini calls, set `gcloud auth application-default login` once.
- If a milestone is too big for one run, tell Claude Code "do step 1 and 2 only, then stop."
```
