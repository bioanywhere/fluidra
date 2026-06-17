import { Chat } from "@/components/Chat";

export default function Home() {
  return (
    <main className="mx-auto flex h-[100dvh] max-w-2xl flex-col p-3 sm:p-4">
      <header className="pb-3">
        <h1 className="text-lg font-semibold">Fluidra Pool Assistant</h1>
        <p className="text-sm text-slate-500">
          Grounded answers from official manuals. Safety first.
        </p>
        <nav className="mt-2 flex flex-wrap gap-2 text-xs">
          <a href="/requirements.html" className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-600 hover:bg-slate-50">📖 Requirement</a>
          <a href="/blueprint.html" className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-600 hover:bg-slate-50">📘 Blueprint</a>
          <a href="/docs" className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-600 hover:bg-slate-50">🧪 API</a>
          <a href="/admin" className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-600 hover:bg-slate-50">🔐 Admin</a>
        </nav>
      </header>
      <Chat />
    </main>
  );
}
