export function TypingIndicator() {
  return (
    <div
      className="flex items-center gap-1 self-start rounded-2xl bg-white px-4 py-3 shadow-sm"
      aria-label="Assistant is typing"
      role="status"
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: `${i * 0.15}s` }}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
