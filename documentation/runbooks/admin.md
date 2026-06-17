# Corpus admin — managing the manuals

A small, token-gated admin surface to manage the manual corpus **without a
rebuild or batch job**. It writes to the same pgvector table the chat endpoint
reads, so changes are live on the next question.

- **Page:** `http://8.233.81.31/admin` (linked as 🔐 Admin from the chat header)
- **API:** `…/v1/admin/*` on chat-api (the load balancer routes `/v1/*` there)

## What you can do

- **List** every indexed document (built-in manifest manuals appear too).
- **Upload** a `.pdf` / `.md` / `.txt` with `doc_id`, `brand`, `model`, optional
  `url` (the citation source) and `locale`. The file is parsed → chunked →
  embedded (Vertex `text-embedding-005`) → indexed. Re-uploading the same
  `doc_id` **replaces** its chunks. Originals are kept (in Postgres) so you can
  re-download them.
- **Delete** a document (removes its chunks + stored original).

## Auth (important)

App auth is still a dev stub, so the admin API is gated by its own token and
**fails closed**: if `ADMIN_TOKEN` is unset on chat-api, every `/v1/admin/*`
call returns `503`. With it set, requests must send `X-Admin-Token: <token>`
(the page prompts for it and keeps it in the browser only).

Set / rotate the token on the running service:

```bash
gcloud run services update chat-api --region=europe-west1 --project=fluidra-499509 \
  --update-env-vars ADMIN_TOKEN=<token>
```

To make it survive a `terraform apply`, set it in
`infrastructure/terraform/envs/dev/terraform.tfvars`:

```hcl
admin_token = "<token>"
```

(If you apply without setting it, `ADMIN_TOKEN` becomes empty and admin disables
— the safe direction.)

## API quick reference

```bash
BASE=http://8.233.81.31 ; TOK=<token>
curl -s "$BASE/v1/admin/documents" -H "X-Admin-Token: $TOK"
curl -s -X POST "$BASE/v1/admin/documents" -H "X-Admin-Token: $TOK" \
  -F file=@manual.pdf -F doc_id=H0639400 -F brand=Jandy -F model=TruClear \
  -F url=https://www.jandy.com/...
curl -s -X DELETE "$BASE/v1/admin/documents/H0639400" -H "X-Admin-Token: $TOK"
```

## Notes / limits

- Upload cap 25 MB (Cloud Run caps requests at 32 MB). PDFs are extracted with
  `pypdf` (text layer only — scanned PDFs need OCR, a Target-state Document AI step).
- Ingestion is synchronous; a very large manual embeds in one Vertex call
  (practical cap a few hundred chunks).
- The batch path still exists (`gcloud run jobs execute ingestion-worker`) for
  re-ingesting the whole baked-in manifest; the admin page is for incremental,
  ad-hoc changes. See [deploy.md](deploy.md).
```
