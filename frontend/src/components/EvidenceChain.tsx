"use client";

import type { EvidenceItem } from "@/lib/api";

const KIND_ICONS: Record<string, string> = {
  code: "⟨/⟩",
  commit: "⎇",
  pull_request: "⇄",
  issue: "#",
  author: "@",
  text: "¶",
};

const KIND_COLORS: Record<string, string> = {
  code: "border-violet-500/40 bg-violet-500/10 text-violet-300",
  commit: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  pull_request: "border-sky-500/40 bg-sky-500/10 text-sky-300",
  issue: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  author: "border-pink-500/40 bg-pink-500/10 text-pink-300",
  text: "border-slate-500/40 bg-slate-500/10 text-slate-300",
};

interface Props {
  items: EvidenceItem[];
}

export function EvidenceChain({ items }: Props) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-slate-500">No structured evidence links extracted from this answer.</p>
    );
  }

  return (
    <div className="relative space-y-0">
      <div className="absolute left-5 top-4 bottom-4 w-px bg-gradient-to-b from-sky-500/50 via-slate-600/30 to-transparent" />
      {items.map((item, i) => {
        const color = KIND_COLORS[item.kind] ?? KIND_COLORS.text;
        const icon = KIND_ICONS[item.kind] ?? "•";
        const content = (
          <div className="flex items-start gap-4">
            <div
              className={`relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border font-mono text-sm ${color}`}
            >
              {icon}
            </div>
            <div className="min-w-0 flex-1 pb-6">
              <p className="text-xs uppercase tracking-wider text-slate-500">{item.kind.replace("_", " ")}</p>
              <p className="font-medium text-slate-200">{item.label}</p>
              {item.snippet && (
                <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900/60 p-3 font-mono text-xs text-slate-400">
                  {item.snippet}
                </pre>
              )}
            </div>
          </div>
        );

        return item.url ? (
          <a
            key={`${item.kind}-${item.label}-${i}`}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block rounded-xl transition hover:bg-slate-800/30"
          >
            {content}
          </a>
        ) : (
          <div key={`${item.kind}-${item.label}-${i}`}>{content}</div>
        );
      })}
    </div>
  );
}
