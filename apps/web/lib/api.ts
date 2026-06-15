import type { ChatResponse } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

export async function postChat(
  conversationId: string,
  message: string,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
  if (!res.ok) {
    throw new Error(`chat request failed: ${res.status}`);
  }
  return (await res.json()) as ChatResponse;
}
