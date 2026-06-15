import type { ChatMessage } from "@/lib/types";
import { AnswerMessage } from "./AnswerMessage";
import { DosingCard } from "./DosingCard";
import { EscalationCard } from "./EscalationCard";

// Routes a message to its tier-aware renderer (§7.3).
export function Message({
  message,
  onSend,
  streaming,
}: {
  message: ChatMessage;
  onSend: (text: string) => void;
  streaming?: boolean;
}) {
  if (message.role === "user") {
    return (
      <div className="max-w-[85%] self-end rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-3 text-sm text-white">
        {message.content}
      </div>
    );
  }

  switch (message.type) {
    case "dosing_prompt":
      return <DosingCard message={message} onSend={onSend} disabled={streaming} />;
    case "escalation":
      return <EscalationCard message={message} />;
    case "answer":
    default:
      return <AnswerMessage message={message} />;
  }
}
