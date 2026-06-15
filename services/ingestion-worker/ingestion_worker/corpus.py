"""
Corpus ingestion — ingest the whole priority-manual set from a manifest.

A manifest (data/manuals/manifest.yaml) lists each manual's path + provenance,
so adding a manual is a data change, not a code change. Reused by the ingestion
job, the eval-runner, and tests.

CLI:  uv run python -m ingestion_worker.corpus --store pgvector --backend vertex
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from .embeddings import get_embedder
from .pipeline import IngestResult, ingest
from .vectorstore import InMemoryVectorStore, VectorStore, get_vector_store

DEFAULT_MANIFEST = Path(__file__).resolve().parents[3] / "data" / "manuals" / "manifest.yaml"


@dataclass
class ManualSpec:
    path: str
    doc_id: str
    brand: str
    model: str
    url: str
    locale: str = "en"


def load_manifest(manifest_path: str | Path = DEFAULT_MANIFEST) -> list[ManualSpec]:
    manifest_path = Path(manifest_path)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    return [
        ManualSpec(
            path=str(base / m["path"]),
            doc_id=m["doc_id"], brand=m["brand"], model=m["model"],
            url=m["url"], locale=m.get("locale", "en"),
        )
        for m in data["manuals"]
    ]


def ingest_corpus(
    store: VectorStore,
    embedder,
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, IngestResult]:
    """Ingest every manual in the manifest into the store. Returns per-doc results."""
    results: dict[str, IngestResult] = {}
    for spec in load_manifest(manifest_path):
        results[spec.doc_id] = ingest(
            spec.path, doc_id=spec.doc_id, brand=spec.brand, model=spec.model,
            url=spec.url, locale=spec.locale, embedder=embedder, store=store,
        )
    return results


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ingest the full manual corpus from the manifest.")
    p.add_argument("--store", choices=["inmemory", "pgvector", "vertex"], default="pgvector")
    p.add_argument("--backend", choices=["auto", "fake", "vertex"], default="auto")
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = p.parse_args(argv)

    if args.backend != "auto":
        os.environ["EMBEDDING_BACKEND"] = args.backend
    embedder = get_embedder()
    store = (
        InMemoryVectorStore()
        if args.store == "inmemory"
        else get_vector_store(embedder.dim, backend=args.store)
    )

    results = ingest_corpus(store, embedder, args.manifest)
    total = sum(r.chunks for r in results.values())
    print(f"Ingested {len(results)} manuals, {total} chunks ({embedder.name}, {args.store}):")
    for doc_id, r in results.items():
        print(f"  {doc_id}: {r.chunks} chunks")
    print(f"store now holds {store.count()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
