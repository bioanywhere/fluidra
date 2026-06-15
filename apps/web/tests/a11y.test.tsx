import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "jest-axe";

import { Message } from "@/components/Message";
import type { ChatMessage } from "@/lib/types";

const onSend = () => {};

const messages: ChatMessage[] = [
  { id: "u", role: "user", content: "my salt system shows code 125" },
  {
    id: "a", role: "assistant", tier: "T1", type: "answer",
    content: "The flow switch is not detecting flow.",
    citations: [{ doc_id: "H0567500", section: "Service Code 125", brand: "Jandy", url: "https://example" }],
  },
  {
    id: "d", role: "assistant", tier: "T2", type: "dosing_prompt",
    content: "I need volume and reading.",
    warnings: ["Never mix pool chemicals together."],
  },
  {
    id: "e", role: "assistant", tier: "T3", type: "escalation",
    content: "Please stop using the equipment.",
  },
];

describe("accessibility (§7.5)", () => {
  it("the message list has no axe violations", async () => {
    const { container } = render(
      <main>
        <h1>Fluidra Pool Assistant</h1>
        <section aria-label="Pool assistant chat">
          <ol aria-live="polite">
            {messages.map((m) => (
              <li key={m.id}>
                <Message message={m} onSend={onSend} />
              </li>
            ))}
          </ol>
        </section>
      </main>,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
