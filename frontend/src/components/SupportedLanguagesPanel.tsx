"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { LanguageInfo } from "@/lib/api";

export function SupportedLanguagesPanel() {
  const [open, setOpen] = useState(false);
  const [languages, setLanguages] = useState<LanguageInfo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || languages.length > 0) return;
    setLoading(true);
    api
      .supportedLanguages()
      .then(setLanguages)
      .catch(() => setLanguages([]))
      .finally(() => setLoading(false));
  }, [open, languages.length]);

  const count = languages.length;

  return (
    <div className="mt-6">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-slate-500 transition hover:text-slate-300"
      >
        {open ? "Hide" : "View"} supported languages
        {count > 0 ? ` (${count})` : ""}
      </button>
      {open && (
        <div className="mt-3 max-h-48 overflow-y-auto rounded-xl border border-slate-700/40 bg-slate-900/30 p-3">
          {loading && <p className="text-xs text-slate-500">Loading…</p>}
          {!loading && languages.length === 0 && (
            <p className="text-xs text-slate-500">Could not load language list.</p>
          )}
          <div className="flex flex-wrap gap-1.5">
            {languages.map((lang) => (
              <span
                key={lang.id}
                title={lang.extensions.join(", ")}
                className="rounded-full border border-slate-700/50 px-2 py-0.5 text-[10px] text-slate-400"
              >
                {lang.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
