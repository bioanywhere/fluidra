"use client";

import { useChat } from "@/lib/useChat";
import { Composer } from "./Composer";
import { Message } from "./Message";
import { TypingIndicator } from "./TypingIndicator";

const SUGGESTIONS = [
  "My salt system shows code 125",
  "How much chlorine should I add",
  "There's a burning smell from my heater",
];

export function Chat() {
  const { messages, send, streaming } = useChat();

  return (
    <section
      aria-label="Pool assistant chat"
      className="flex min-h-0 flex-1 flex-col"
    >
      <ol
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pb-2"
        aria-live="polite"
        aria-relevant="additions"
      >
        {messages.length === 0 && (
          <li className="mt-2 flex flex-col gap-2">
            <p className="text-sm text-slate-500">Try one of these:</p>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                className="self-start rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"
              >
                {s}
              </button>
            ))}
          </li>
        )}

        {messages.map((m) => (
          <li key={m.id} className="flex flex-col">
            <Message message={m} onSend={send} streaming={streaming} />
          </li>
        ))}

        {streaming && (
          <li className="flex flex-col">
            <TypingIndicator />
          </li>
        )}
      </ol>

      <Composer onSend={send} disabled={streaming} />
    </section>
  );
}
