// Mirrors the backend shared_types.ChatResponse (Pydantic). A Pydantic -> TS
// codegen step (packages/shared-types) is a future enhancement; until then these
// are kept in sync by hand.

export type Tier = "T1" | "T2" | "T3";
export type ResponseType = "answer" | "dosing_prompt" | "escalation";

export interface Citation {
  doc_id: string;
  section: string;
  brand?: string | null;
  url?: string | null;
}

export interface ChatResponse {
  tier: Tier;
  type: ResponseType;
  content: string;
  citations: Citation[];
  warnings: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tier?: Tier;
  type?: ResponseType;
  citations?: Citation[];
  warnings?: string[];
}
