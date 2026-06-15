import type { Citation } from "@/lib/types";

function shortSection(section: string): string {
  const parts = section.split(">");
  return (parts[parts.length - 1] ?? section).trim();
}

export function Citations({ citations }: { citations: Citation[] }) {
  if (!citations || citations.length === 0) return null;
  return (
    <ul className="mt-2 flex flex-wrap gap-2" aria-label="Sources">
      {citations.map((c, i) => {
        const label = `Source: ${c.brand ? c.brand + " — " : ""}§${shortSection(c.section)}`;
        const chipClass =
          "inline-flex items-center rounded-full border border-slate-300 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600";
        return (
          <li key={`${c.doc_id}-${i}`}>
            {c.url ? (
              <a
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className={chipClass + " hover:bg-slate-100"}
                title={c.section}
              >
                {label}
              </a>
            ) : (
              <span className={chipClass} title={c.section}>
                {label}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
