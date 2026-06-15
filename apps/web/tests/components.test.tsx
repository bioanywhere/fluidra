import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AnswerMessage } from "@/components/AnswerMessage";
import { DosingCard } from "@/components/DosingCard";
import { EscalationCard } from "@/components/EscalationCard";
import type { ChatMessage } from "@/lib/types";

describe("tier-aware message rendering (§7.3)", () => {
  it("T1 answer shows content and a tappable citation chip", () => {
    const m: ChatMessage = {
      id: "1", role: "assistant", tier: "T1", type: "answer",
      content: "Check the flow switch.",
      citations: [
        { doc_id: "H0567500", section: "Service Codes > Service Code 125", brand: "Jandy", url: "https://example/manual" },
      ],
    };
    render(<AnswerMessage message={m} />);
    expect(screen.getByText("Check the flow switch.")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Service Code 125/ });
    expect(link).toHaveAttribute("href", "https://example/manual");
  });

  it("T3 escalation shows safety heading + stop-use content in a labelled region", () => {
    const m: ChatMessage = {
      id: "2", role: "assistant", tier: "T3", type: "escalation",
      content: "Please stop using the equipment now.",
    };
    render(<EscalationCard message={m} />);
    expect(screen.getByText(/Safety first/)).toBeInTheDocument();
    expect(screen.getByText("Please stop using the equipment now.")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /Safety escalation/i })).toBeInTheDocument();
  });

  it("T2 dosing card shows safety warnings and submits structured inputs", async () => {
    const onSend = vi.fn();
    const m: ChatMessage = {
      id: "3", role: "assistant", tier: "T2", type: "dosing_prompt",
      content: "I need the pool volume and current reading.",
      warnings: ["Never mix pool chemicals together — add each one separately to the water."],
    };
    render(<DosingCard message={m} onSend={onSend} />);
    expect(screen.getByText(/Never mix/)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/Volume/), "50");
    await user.type(screen.getByLabelText(/Current/), "1");
    await user.type(screen.getByLabelText(/Target/), "3");
    await user.click(screen.getByRole("button", { name: /Calculate dose/ }));

    expect(onSend).toHaveBeenCalledWith("50 m3, current chlorine 1 ppm, target 3 ppm");
  });

  it("dosing calculate button is disabled until volume + current are entered", () => {
    const m: ChatMessage = {
      id: "4", role: "assistant", tier: "T2", type: "dosing_prompt",
      content: "I need inputs.", warnings: [],
    };
    render(<DosingCard message={m} onSend={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Calculate dose/ })).toBeDisabled();
  });
});
