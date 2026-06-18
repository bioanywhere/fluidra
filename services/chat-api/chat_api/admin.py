"""
Admin API for the manual corpus (blueprint §8 — corpus administration).

Token-gated: every request must carry `X-Admin-Token` equal to the service's
`ADMIN_TOKEN`. Fail-closed — if `ADMIN_TOKEN` is unset the endpoints return 503,
so the corpus can never be mutated by an unauthenticated caller (app auth is a
dev stub today).

It lets an operator:
  - list the documents currently indexed (derived from the live vector store,
    so built-in manifest manuals appear too);
  - upload a manual (PDF/MD/TXT) → parse → chunk → embed → index, *replacing*
    any chunks with the same doc_id (clean re-ingest);
  - download the original file again; delete a document.

chat-api reads the same pgvector table the chat endpoint retrieves from, so a
change here is live on the next question — no redeploy, no batch job.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from ingestion_worker.pipeline import ingest

from .config import settings
from .rag import get_rag

router = APIRouter(prefix="/v1/admin", tags=["admin"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # Cloud Run caps requests at 32 MB
ALLOWED_SUFFIXES = {".pdf", ".md", ".markdown", ".txt"}


def _admin_token() -> str:
    return settings.admin_token or os.getenv("ADMIN_TOKEN", "")


def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    token = _admin_token()
    if not token:
        raise HTTPException(status_code=503, detail="admin disabled (ADMIN_TOKEN not set)")
    if not x_admin_token or x_admin_token != token:
        raise HTTPException(status_code=401, detail="invalid admin token")


# ── original-file store (Postgres; metadata + bytea, split so listing is light) ─
_files_engine = None


def _engine():
    global _files_engine
    if _files_engine is None:
        dsn = os.getenv("DATABASE_URL_SYNC", settings.database_url_sync)
        eng = create_engine(dsn)
        with eng.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS manual_files (
                        doc_id       TEXT PRIMARY KEY,
                        filename     TEXT,
                        content_type TEXT,
                        size_bytes   INTEGER,
                        sha256       TEXT,
                        brand        TEXT,
                        model        TEXT,
                        url          TEXT,
                        locale       TEXT,
                        uploaded_at  TIMESTAMPTZ,
                        doc_type     TEXT
                    )
                    """
                )
            )
            # doc_type was added later; ensure it exists on pre-existing tables.
            conn.execute(text("ALTER TABLE manual_files ADD COLUMN IF NOT EXISTS doc_type TEXT"))
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS manual_file_blobs (
                        doc_id TEXT PRIMARY KEY,
                        data   BYTEA NOT NULL
                    )
                    """
                )
            )
        _files_engine = eng
    return _files_engine


@router.get("/documents")
async def list_documents(_: None = Depends(require_admin), rag=Depends(get_rag)):
    """All indexed documents, enriched with upload metadata when present."""
    store = rag[0]

    def _list():
        docs = store.list_documents()
        meta: dict[str, dict] = {}
        with _engine().connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT doc_id, filename, content_type, size_bytes, uploaded_at, doc_type "
                    "FROM manual_files"
                )
            ).mappings()
            for r in rows:
                meta[r["doc_id"]] = dict(r)
        for d in docs:
            m = meta.get(d["doc_id"])
            d["filename"] = m["filename"] if m else None
            d["size_bytes"] = m["size_bytes"] if m else None
            d["doc_type"] = m["doc_type"] if m else None
            d["uploaded_at"] = (
                m["uploaded_at"].isoformat() if m and m["uploaded_at"] else None
            )
            # a metadata-only row (edited built-in) has no filename/blob
            d["has_file"] = bool(m and m["filename"])
        return docs

    return {"documents": await run_in_threadpool(_list)}


@router.post("/documents")
async def upload_document(
    _: None = Depends(require_admin),
    file: UploadFile = File(...),
    doc_id: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    url: str = Form(""),
    locale: str = Form("en"),
    doc_type: str = Form(""),
    rag=Depends(get_rag),
):
    """Ingest (or re-ingest) one manual. Replaces all chunks for `doc_id`."""
    doc_id = doc_id.strip()
    if not doc_id or not brand.strip() or not model.strip():
        raise HTTPException(422, "doc_id, brand and model are required")
    raw = await file.read()
    if not raw:
        raise HTTPException(422, "empty file")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"file too large (>{MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, f"unsupported type {suffix!r}; allowed: pdf, md, txt")

    store, embedder, _llm = rag

    def _ingest_and_store():
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
        try:
            store.delete_document(doc_id)  # clean replace (avoid orphan chunks)
            result = ingest(
                tmp_path, doc_id=doc_id, brand=brand, model=model, url=url,
                locale=locale, embedder=embedder, store=store,
            )
        finally:
            os.unlink(tmp_path)

        eng = _engine()
        with eng.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO manual_files
                      (doc_id, filename, content_type, size_bytes, sha256,
                       brand, model, url, locale, uploaded_at, doc_type)
                    VALUES
                      (:doc_id, :filename, :content_type, :size_bytes, :sha256,
                       :brand, :model, :url, :locale, :uploaded_at, :doc_type)
                    ON CONFLICT (doc_id) DO UPDATE SET
                      filename=EXCLUDED.filename, content_type=EXCLUDED.content_type,
                      size_bytes=EXCLUDED.size_bytes, sha256=EXCLUDED.sha256,
                      brand=EXCLUDED.brand, model=EXCLUDED.model, url=EXCLUDED.url,
                      locale=EXCLUDED.locale, uploaded_at=EXCLUDED.uploaded_at,
                      doc_type=EXCLUDED.doc_type
                    """
                ),
                {
                    "doc_id": doc_id, "filename": file.filename,
                    "content_type": file.content_type, "size_bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(), "brand": brand,
                    "model": model, "url": url, "locale": locale,
                    "uploaded_at": datetime.now(timezone.utc),
                    "doc_type": doc_type or None,
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO manual_file_blobs (doc_id, data) VALUES (:doc_id, :data)
                    ON CONFLICT (doc_id) DO UPDATE SET data = EXCLUDED.data
                    """
                ),
                {"doc_id": doc_id, "data": raw},
            )
        return result

    result = await run_in_threadpool(_ingest_and_store)
    return {
        "doc_id": result.doc_id, "chunks": result.chunks,
        "embedded": result.embedded, "indexed": result.indexed,
        "embedder": embedder.name,
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, _: None = Depends(require_admin), rag=Depends(get_rag)):
    store = rag[0]

    def _delete():
        removed = store.delete_document(doc_id)
        with _engine().begin() as conn:
            conn.execute(text("DELETE FROM manual_files WHERE doc_id = :d"), {"d": doc_id})
            conn.execute(text("DELETE FROM manual_file_blobs WHERE doc_id = :d"), {"d": doc_id})
        return removed

    removed = await run_in_threadpool(_delete)
    if removed == 0:
        raise HTTPException(404, f"no chunks found for doc_id {doc_id!r}")
    return {"doc_id": doc_id, "deleted_chunks": removed}


class DocMetaPatch(BaseModel):
    brand: str | None = None
    model: str | None = None
    doc_type: str | None = None
    url: str | None = None
    locale: str | None = None


@router.patch("/documents/{doc_id}")
async def update_document_metadata(
    doc_id: str,
    patch: DocMetaPatch,
    _: None = Depends(require_admin),
    rag=Depends(get_rag),
):
    """Edit a document's metadata. brand/model/url/locale propagate to the
    retrieval chunks (so future citations reflect the change); doc_type is
    document-level. No re-embedding — metadata only."""
    store = rag[0]
    fields = {k: v for k, v in patch.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(422, "no fields to update")

    def _update():
        if doc_id not in {d["doc_id"] for d in store.list_documents()}:
            return False
        with _engine().begin() as conn:
            # retrieval chunks carry brand/model/url/locale (table name is the
            # PgVectorStore default); doc_type is document-level only.
            chunk_fields = {k: fields[k] for k in ("brand", "model", "url", "locale") if k in fields}
            if chunk_fields:
                sets = ", ".join(f"{k} = :{k}" for k in chunk_fields)
                conn.execute(
                    text(f"UPDATE manual_chunks SET {sets} WHERE doc_id = :doc_id"),
                    {**chunk_fields, "doc_id": doc_id},
                )
            meta_fields = {k: fields[k] for k in ("brand", "model", "url", "locale", "doc_type") if k in fields}
            if meta_fields:
                sets = ", ".join(f"{k} = :{k}" for k in meta_fields)
                res = conn.execute(
                    text(f"UPDATE manual_files SET {sets} WHERE doc_id = :doc_id"),
                    {**meta_fields, "doc_id": doc_id},
                )
                if (res.rowcount or 0) == 0:  # built-in doc: create a metadata-only row
                    icols = ["doc_id", *meta_fields.keys()]
                    ph = ", ".join(":" + c for c in icols)
                    conn.execute(
                        text(f"INSERT INTO manual_files ({', '.join(icols)}) VALUES ({ph})"),
                        {"doc_id": doc_id, **meta_fields},
                    )
        return True

    if not await run_in_threadpool(_update):
        raise HTTPException(404, f"unknown doc_id {doc_id!r}")
    return {"doc_id": doc_id, "updated": sorted(fields.keys())}


@router.get("/documents/{doc_id}/file")
async def download_document(doc_id: str, _: None = Depends(require_admin)):
    def _get():
        with _engine().connect() as conn:
            meta = conn.execute(
                text("SELECT filename, content_type FROM manual_files WHERE doc_id = :d"),
                {"d": doc_id},
            ).mappings().first()
            blob = conn.execute(
                text("SELECT data FROM manual_file_blobs WHERE doc_id = :d"), {"d": doc_id}
            ).scalar()
        return meta, blob

    meta, blob = await run_in_threadpool(_get)
    if blob is None:
        raise HTTPException(404, "no original file stored for this document")
    filename = (meta["filename"] if meta else None) or f"{doc_id}"
    return Response(
        content=bytes(blob),
        media_type=(meta["content_type"] if meta else None) or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
