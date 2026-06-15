"use client";

import { useState } from "react";

export function Composer({
  onSend,
  disabled,
  maxLength = 2000,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
  maxLength?: number;
}) {
  const [value, setValue] = useState("");

  function submit() {
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  }

  return (
    <form
      className="mt-3 flex items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <label htmlFor="composer-input" className="sr-only">
        Message the pool assistant
      </label>
      <textarea
        id="composer-input"
        className="min-h-[44px] flex-1 resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600"
        rows={1}
        maxLength={maxLength}
        value={value}
        placeholder="Ask about a fault code, dosing, or a problem…"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="h-[44px] rounded-xl bg-blue-600 px-4 text-sm font-medium text-white disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
      >
        Send
      </button>
    </form>
  );
}
