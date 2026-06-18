import type { ChatResponse } from "./types";
import { getIdToken } from "./auth";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

export async function postChat(
  conversationId: string,
  message: string,
): Promise<ChatResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  // When Firebase auth is on, attach the user's ID token (ignored by the
  // backend in stub mode, verified in firebase mode).
  const token = await getIdToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/v1/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
  if (!res.ok) {
    throw new Error(`chat request failed: ${res.status}`);
  }
  return (await res.json()) as ChatResponse;
}
