import type { ChatMessage } from "@/lib/types";
import { Citations } from "./Citations";

// Tier-1: neutral answer bubble + tappable citation chips (§7.3).
export function AnswerMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="max-w-[85%] self-start rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <p className="whitespace-pre-wrap text-sm text-slate-800">{message.content}</p>
      <Citations citations={message.citations ?? []} />
    </div>
  );
}
