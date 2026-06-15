"use client";

import { useState } from "react";
import type { ChatMessage } from "@/lib/types";

// Tier-2: structured dosing card with input slots -> result + fixed safety
// warnings (§7.3, §7.4). Numbers never come from the LLM; submitting the inputs
// sends a structured message that the deterministic calculator answers.
export function DosingCard({
  message,
  onSend,
  disabled,
}: {
  message: ChatMessage;
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [volume, setVolume] = useState("");
  const [current, setCurrent] = useState("");
  const [target, setTarget] = useState("");

  const isPrompt = message.type === "dosing_prompt";

  function calculate() {
    if (!volume || !current) return;
    const tgt = target ? `, target ${target} ppm` : "";
    onSend(`${volume} m3, current chlorine ${current} ppm${tgt}`);
  }

  const field =
    "w-full rounded-md border border-slate-300 px-2 py-1 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-tier-dosing";

  return (
    <section
      aria-label="Dosing helper"
      className="max-w-[90%] self-start rounded-2xl border-l-4 border-tier-dosing bg-white px-4 py-3 shadow-sm"
    >
      <h2 className="text-sm font-semibold text-tier-dosing">Dosing helper</h2>
      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">{message.content}</p>

      {isPrompt && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          <label className="text-xs text-slate-600">
            Volume (m³)
            <input
              className={field}
              inputMode="decimal"
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
            />
          </label>
          <label className="text-xs text-slate-600">
            Current (ppm)
            <input
              className={field}
              inputMode="decimal"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </label>
          <label className="text-xs text-slate-600">
            Target (ppm)
            <input
              className={field}
              inputMode="decimal"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </label>
        </div>
      )}

      {isPrompt && (
        <button
          type="button"
          onClick={calculate}
          disabled={disabled || !volume || !current}
          className="mt-3 rounded-md bg-tier-dosing px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tier-dosing"
        >
          Calculate dose
        </button>
      )}

      {message.warnings && message.warnings.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-slate-100 pt-2" aria-label="Safety warnings">
          {message.warnings.map((w, i) => (
            <li key={i} className="flex gap-1.5 text-xs text-slate-600">
              <span aria-hidden="true">•</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
