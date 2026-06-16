"use client";

import { useMutation } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { postChat } from "./api";
import type { ChatMessage } from "./types";

function uid(): string {
  // crypto.randomUUID() only exists in a secure context (HTTPS/localhost); the
  // hosted demo is plain HTTP, so generate an RFC-4122 v4 UUID ourselves.
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function useChat() {
  const [conversationId] = useState(uid);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const append = useCallback((m: ChatMessage) => {
    setMessages((prev) => [...prev, m]);
  }, []);

  const mutation = useMutation({
    mutationFn: (text: string) => postChat(conversationId, text),
    onMutate: (text) => {
      append({ id: uid(), role: "user", content: text });
    },
    onSuccess: (resp) => {
      append({
        id: uid(),
        role: "assistant",
        content: resp.content,
        tier: resp.tier,
        type: resp.type,
        citations: resp.citations,
        warnings: resp.warnings,
      });
    },
    onError: () => {
      append({
        id: uid(),
        role: "assistant",
        content:
          "Sorry — I couldn't reach the assistant. Please try again in a moment.",
        tier: "T3",
        type: "escalation",
      });
    },
  });

  const send = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (trimmed) mutation.mutate(trimmed);
    },
    [mutation],
  );

  return { messages, send, streaming: mutation.isPending };
}
