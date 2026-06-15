import { describe, it, expect, vi, afterEach } from "vitest";
import { postChat } from "@/lib/api";

afterEach(() => vi.restoreAllMocks());

describe("postChat", () => {
  it("posts conversation_id + message and returns the parsed response", async () => {
    const resp = { tier: "T1", type: "answer", content: "hi", citations: [], warnings: [] };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => resp });
    vi.stubGlobal("fetch", fetchMock);

    const out = await postChat("cid-1", "hello");
    expect(out).toEqual(resp);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/v1/chat");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ conversation_id: "cid-1", message: "hello" });
  });

  it("throws on a non-OK response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));
    await expect(postChat("c", "m")).rejects.toThrow(/503/);
  });
});
