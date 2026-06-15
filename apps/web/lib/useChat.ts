"use client";

import { useMutation } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { postChat } from "./api";
import type { ChatMessage } from "./types";

function uid(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
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
