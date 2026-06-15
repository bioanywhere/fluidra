"""
CLI entrypoint:  uv run python -m ingestion_worker.ingest <manual> [options]

Examples:
  # Offline, no DB — parse/chunk/embed the bundled manual, report chunk count:
  uv run python -m ingestion_worker.ingest data/manuals/aquapure_h0567500.md \
      --store inmemory --backend fake

  # Into local pgvector (requires `make dev` Postgres with the pgvector image):
  uv run python -m ingestion_worker.ingest data/manuals/aquapure_h0567500.md \
      --store pgvector --dsn postgresql+psycopg2://postgres:localdev@localhost:5432/assistant
"""
from __future__ import annotations

import argparse
import os
import sys

from .embeddings import get_embedder
from .pipeline import ingest
from .vectorstore import InMemoryVectorStore, get_vector_store

# Defaults describe the bundled dev manual.
DEFAULTS = {
    "doc_id": "H0567500",
    "brand": "Jandy",
    "model": "AquaPure",
    "url": "https://www.jandy.com/en/products/sanitizers/aquapure",
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ingest one manual into the vector store.")
    p.add_argument("source", help="Path to a .md/.txt/.pdf manual")
    p.add_argument("--doc-id", default=DEFAULTS["doc_id"])
    p.add_argument("--brand", default=DEFAULTS["brand"])
    p.add_argument("--model", default=DEFAULTS["model"])
    p.add_argument("--url", default=DEFAULTS["url"])
    p.add_argument("--locale", default="en")
    p.add_argument("--store", choices=["inmemory", "pgvector", "vertex"], default="pgvector")
    p.add_argument("--backend", choices=["auto", "fake", "vertex"], default="auto",
                   help="embedding backend; overrides EMBEDDING_BACKEND")
    p.add_argument("--dsn",
                   default=os.getenv("DATABASE_URL_SYNC",
                                     "postgresql+psycopg2://postgres:localdev@localhost:5432/assistant"))
    args = p.parse_args(argv)

    if args.backend != "auto":
        os.environ["EMBEDDING_BACKEND"] = args.backend
    embedder = get_embedder()

    if args.store == "inmemory":
        store = InMemoryVectorStore()
    else:
        store = get_vector_store(embedder.dim, backend=args.store, dsn=args.dsn)

    result = ingest(
        args.source,
        doc_id=args.doc_id, brand=args.brand, model=args.model, url=args.url,
        locale=args.locale, embedder=embedder, store=store,
    )

    print(
        f"Ingested '{args.source}'\n"
        f"  doc_id   : {result.doc_id} ({args.brand} {args.model})\n"
        f"  embedder : {embedder.name} (dim={embedder.dim})\n"
        f"  store    : {args.store}\n"
        f"  chunks   : {result.chunks}\n"
        f"  embedded : {result.embedded}\n"
        f"  indexed  : {result.indexed} (store now holds {store.count()})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
