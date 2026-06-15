import type { ChatMessage } from "@/lib/types";

// Tier-3: coral-bordered card, calm tone — stop-use guidance + handoff (§7.3).
export function EscalationCard({ message }: { message: ChatMessage }) {
  return (
    <section
      aria-label="Safety escalation"
      className="max-w-[90%] self-start rounded-2xl border-2 border-tier-escalation bg-orange-50 px-4 py-3"
    >
      <h2 className="flex items-center gap-2 text-sm font-semibold text-tier-escalation">
        <span aria-hidden="true">⚠️</span> Safety first
      </h2>
      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">{message.content}</p>
    </section>
  );
}
