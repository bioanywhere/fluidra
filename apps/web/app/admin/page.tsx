"use client";

import { Fragment, useCallback, useEffect, useState, type FormEvent } from "react";

// Same resolution as lib/api.ts: empty string in prod => same-origin (the load
// balancer routes /v1/* to chat-api); undefined in local dev => localhost:8080.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
const TOKEN_KEY = "fluidra_admin_token";

type Doc = {
  doc_id: string;
  brand: string | null;
  model: string | null;
  url: string | null;
  locale: string | null;
  doc_type: string | null;
  chunks: number;
  filename: string | null;
  size_bytes: number | null;
  uploaded_at: string | null;
  has_file: boolean;
};

function fmtBytes(n: number | null): string {
  if (!n && n !== 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [authed, setAuthed] = useState(false);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // upload form
  const [file, setFile] = useState<File | null>(null);
  const [docId, setDocId] = useState("");
  const [brand, setBrand] = useState("");
  const [model, setModel] = useState("");
  const [url, setUrl] = useState("");
  const [locale, setLocale] = useState("en");
  const [busy, setBusy] = useState(false);

  // inline metadata editor
  const [editing, setEditing] = useState<string | null>(null);
  const [ev, setEv] = useState({ brand: "", model: "", doc_type: "", url: "", locale: "" });
  const [savingEdit, setSavingEdit] = useState(false);

  const headers = useCallback(() => ({ "X-Admin-Token": token }), [token]);

  const load = useCallback(
    async (tok: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/v1/admin/documents`, {
          headers: { "X-Admin-Token": tok },
        });
        if (res.status === 401) throw new Error("Invalid admin token.");
        if (res.status === 503)
          throw new Error("Admin is disabled on the server (ADMIN_TOKEN not set).");
        if (!res.ok) throw new Error(`Request failed (${res.status}).`);
        const data = await res.json();
        setDocs(data.documents ?? []);
        setAuthed(true);
        localStorage.setItem(TOKEN_KEY, tok);
      } catch (e) {
        setAuthed(false);
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (saved) {
      setToken(saved);
      void load(saved);
    }
  }, [load]);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    if (!file) {
      setError("Choose a file first.");
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    fd.append("doc_id", docId);
    fd.append("brand", brand);
    fd.append("model", model);
    fd.append("url", url);
    fd.append("locale", locale);
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/v1/admin/documents`, {
        method: "POST",
        headers: headers(),
        body: fd,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Upload failed (${res.status}).`);
      setNotice(
        `Ingested "${data.doc_id}" — ${data.chunks} chunks indexed (${data.embedder}).`,
      );
      setFile(null);
      setDocId("");
      setBrand("");
      setModel("");
      setUrl("");
      const fi = document.getElementById("file-input") as HTMLInputElement | null;
      if (fi) fi.value = "";
      await load(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm(`Remove "${id}" from the corpus? This deletes its chunks.`)) return;
    setError(null);
    setNotice(null);
    try {
      const res = await fetch(`${API_BASE}/v1/admin/documents/${encodeURIComponent(id)}`, {
        method: "DELETE",
        headers: headers(),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Delete failed (${res.status}).`);
      setNotice(`Removed "${id}" (${data.deleted_chunks} chunks).`);
      await load(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function onDownload(id: string, filename: string | null) {
    // Anchors can't send the auth header, so fetch the blob then save it.
    try {
      const res = await fetch(
        `${API_BASE}/v1/admin/documents/${encodeURIComponent(id)}/file`,
        { headers: headers() },
      );
      if (!res.ok) throw new Error(`Download failed (${res.status}).`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename || id;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function onPickFile(f: File | null) {
    setFile(f);
    if (f && !docId) {
      // suggest a doc_id from the filename (stem, upper, alnum/dash)
      const stem = f.name.replace(/\.[^.]+$/, "");
      setDocId(stem.toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/(^-|-$)/g, ""));
    }
  }

  function startEdit(d: Doc) {
    setError(null);
    setNotice(null);
    setEditing(d.doc_id);
    setEv({
      brand: d.brand ?? "",
      model: d.model ?? "",
      doc_type: d.doc_type ?? "",
      url: d.url ?? "",
      locale: d.locale ?? "",
    });
  }

  async function saveEdit(id: string) {
    if (!ev.brand.trim() || !ev.model.trim()) {
      setError("Brand and model can't be empty.");
      return;
    }
    setSavingEdit(true);
    setError(null);
    setNotice(null);
    try {
      const res = await fetch(`${API_BASE}/v1/admin/documents/${encodeURIComponent(id)}`, {
        method: "PATCH",
        headers: { ...headers(), "Content-Type": "application/json" },
        body: JSON.stringify(ev),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Update failed (${res.status}).`);
      setNotice(`Updated "${id}" (${(data.updated ?? []).join(", ")}).`);
      setEditing(null);
      await load(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSavingEdit(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-4 sm:p-6">
      <header className="mb-5 flex flex-wrap items-center gap-3">
        <h1 className="mr-auto text-xl font-semibold">Corpus admin — manuals</h1>
        <a
          href="/"
          className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-50"
        >
          ← Back to chat
        </a>
      </header>

      {/* token */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
        <label htmlFor="admin-token" className="block text-sm font-medium text-slate-700">
          Admin token
        </label>
        <div className="mt-1 flex flex-wrap gap-2">
          <input
            id="admin-token"
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="X-Admin-Token"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => load(token)}
            disabled={!token || loading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Loading…" : authed ? "Refresh" : "Unlock"}
          </button>
          {authed && (
            <button
              type="button"
              onClick={() => {
                localStorage.removeItem(TOKEN_KEY);
                setToken("");
                setAuthed(false);
                setDocs([]);
              }}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              Lock
            </button>
          )}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          The token is checked server-side and stored only in this browser.
        </p>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {notice && (
        <div className="mb-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">
          {notice}
        </div>
      )}

      {authed && (
        <>
          {/* upload */}
          <form
            onSubmit={onUpload}
            className="mb-6 rounded-xl border border-slate-200 bg-white p-4"
          >
            <h2 className="mb-3 text-sm font-semibold text-slate-700">Add / replace a manual</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="block text-xs text-slate-500">File (PDF, MD, or TXT)</label>
                <input
                  id="file-input"
                  type="file"
                  accept=".pdf,.md,.markdown,.txt"
                  onChange={(e) => onPickFile(e.target.files?.[0] ?? null)}
                  className="mt-1 block w-full text-sm"
                />
              </div>
              <Field label="doc_id *" value={docId} onChange={setDocId} placeholder="H0567500" />
              <Field label="brand *" value={brand} onChange={setBrand} placeholder="Jandy" />
              <Field label="model *" value={model} onChange={setModel} placeholder="AquaPure" />
              <Field label="locale" value={locale} onChange={setLocale} placeholder="en" />
              <div className="sm:col-span-2">
                <Field
                  label="source url (shown as the citation)"
                  value={url}
                  onChange={setUrl}
                  placeholder="https://www.jandy.com/..."
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={busy}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busy ? "Ingesting…" : "Upload & ingest"}
            </button>
            <p className="mt-2 text-xs text-slate-500">
              Parsed → chunked → embedded → indexed. Re-uploading the same doc_id replaces it.
            </p>
          </form>

          {/* list */}
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
                  <th className="p-3">Document</th>
                  <th className="p-3">Doc type</th>
                  <th className="p-3">Chunks</th>
                  <th className="p-3">File</th>
                  <th className="p-3">Uploaded</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {docs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-slate-400">
                      No documents indexed yet.
                    </td>
                  </tr>
                )}
                {docs.map((d) => (
                  <Fragment key={d.doc_id}>
                    <tr className="border-b border-slate-100">
                      <td className="p-3">
                        <div className="font-medium text-slate-800">{d.doc_id}</div>
                        <div className="text-xs text-slate-500">
                          {[d.brand, d.model].filter(Boolean).join(" · ") || "—"}
                        </div>
                      </td>
                      <td className="p-3 text-slate-600">{d.doc_type || "—"}</td>
                      <td className="p-3 tabular-nums">{d.chunks}</td>
                      <td className="p-3">
                        {d.has_file ? (
                          <span title={d.filename ?? ""}>{fmtBytes(d.size_bytes)}</span>
                        ) : (
                          <span className="text-slate-400">built-in</span>
                        )}
                      </td>
                      <td className="p-3 text-slate-500">
                        {d.uploaded_at ? new Date(d.uploaded_at).toLocaleString() : "—"}
                      </td>
                      <td className="p-3">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => (editing === d.doc_id ? setEditing(null) : startEdit(d))}
                            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
                          >
                            {editing === d.doc_id ? "Close" : "Edit"}
                          </button>
                          {d.has_file && (
                            <button
                              type="button"
                              onClick={() => onDownload(d.doc_id, d.filename)}
                              className="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
                            >
                              Download
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => onDelete(d.doc_id)}
                            className="rounded-md border border-red-200 px-2.5 py-1 text-xs text-red-600 hover:bg-red-50"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                    {editing === d.doc_id && (
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <td colSpan={6} className="p-4">
                          <div className="grid gap-3 sm:grid-cols-2">
                            <Field label="brand *" value={ev.brand} onChange={(v) => setEv({ ...ev, brand: v })} />
                            <Field label="model *" value={ev.model} onChange={(v) => setEv({ ...ev, model: v })} />
                            <Field label="doc type" value={ev.doc_type} onChange={(v) => setEv({ ...ev, doc_type: v })} placeholder="installation_manual, brochure, datasheet…" />
                            <Field label="locale" value={ev.locale} onChange={(v) => setEv({ ...ev, locale: v })} placeholder="en" />
                            <div className="sm:col-span-2">
                              <Field label="source url (citation)" value={ev.url} onChange={(v) => setEv({ ...ev, url: v })} />
                            </div>
                          </div>
                          <div className="mt-3 flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => saveEdit(d.doc_id)}
                              disabled={savingEdit}
                              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                            >
                              {savingEdit ? "Saving…" : "Save metadata"}
                            </button>
                            <button
                              type="button"
                              onClick={() => setEditing(null)}
                              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-white"
                            >
                              Cancel
                            </button>
                            <span className="text-xs text-slate-500">
                              brand/model/url propagate to citations; no re-embedding.
                            </span>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}

function Field(props: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-slate-500">{props.label}</label>
      <input
        type="text"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        placeholder={props.placeholder}
        className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      />
    </div>
  );
}
