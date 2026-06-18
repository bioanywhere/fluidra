"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { currentUser, firebaseEnabled, signIn, signOut } from "@/lib/auth";

function useAuthUser() {
  const [user, setUser] = useState<{ email: string; uid: string } | null>(null);
  useEffect(() => {
    const sync = () => setUser(currentUser());
    sync();
    window.addEventListener("fb-auth", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("fb-auth", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return user;
}

export function AuthGate({ children }: { children: ReactNode }) {
  const user = useAuthUser();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Auth disabled (no Firebase config) → run anonymously, as today.
  if (!firebaseEnabled()) return <>{children}</>;

  if (user) {
    return (
      <>
        <div className="mb-2 flex items-center justify-end gap-2 text-xs text-slate-500">
          <span>{user.email}</span>
          <button
            type="button"
            onClick={signOut}
            className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-600 hover:bg-slate-50"
          >
            Sign out
          </button>
        </div>
        {children}
      </>
    );
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await signIn(email.trim(), pw);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message.replace(/_/g, " ").toLowerCase() : "sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-8 w-full max-w-sm rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold">Sign in</h2>
      <p className="mt-1 text-sm text-slate-500">Use your Fluidra Pool account to continue.</p>
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="email"
        className="mt-3 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      />
      <input
        type="password"
        required
        value={pw}
        onChange={(e) => setPw(e.target.value)}
        placeholder="password"
        className="mt-2 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      />
      {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      <button
        type="submit"
        disabled={busy}
        className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {busy ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
