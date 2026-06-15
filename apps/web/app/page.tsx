import { Chat } from "@/components/Chat";

export default function Home() {
  return (
    <main className="mx-auto flex h-[100dvh] max-w-2xl flex-col p-3 sm:p-4">
      <header className="pb-3">
        <h1 className="text-lg font-semibold">Fluidra Pool Assistant</h1>
        <p className="text-sm text-slate-500">
          Grounded answers from official manuals. Safety first.
        </p>
      </header>
      <Chat />
    </main>
  );
}
