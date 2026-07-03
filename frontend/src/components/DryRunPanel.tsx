"use client";

import type { DryRunEstimate } from "@/lib/api";
import { LanguageRequestForm } from "@/components/LanguageRequestForm";

interface Props {
  estimate: DryRunEstimate;
  owner: string;
  name: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirming: boolean;
}

export function DryRunPanel({ estimate, owner, name, onConfirm, onCancel, confirming }: Props) {
  const unsupported = estimate.unsupported_extensions ?? {};
  const unsupportedList = Object.entries(unsupported);
  const hasGaps = unsupportedList.length > 0 || estimate.file_count === 0;
  const defaultExtensions = unsupportedList.map(([ext]) => ext).join(", ");

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-amber-400/80">Dry-run estimate</p>
          <h3 className="font-serif text-2xl text-slate-100">
            {owner}/{name}
          </h3>
          {estimate.supported_language_count ? (
            <p className="mt-1 text-xs text-slate-500">
              {estimate.supported_language_count}+ languages supported in Code Archaeologist
            </p>
          ) : null}
        </div>
        <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs text-amber-300">
          Confirm before ingest
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Files", value: estimate.file_count },
          { label: "Chunks", value: estimate.chunk_count },
          { label: "Est. LLM calls", value: estimate.estimated_llm_calls },
          { label: "Est. cost", value: `$${estimate.estimated_cost_usd.toFixed(2)}` },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-slate-700/40 bg-slate-900/40 px-4 py-3"
          >
            <p className="text-xs text-slate-500">{stat.label}</p>
            <p className="font-mono text-lg font-medium text-slate-100">{stat.value}</p>
          </div>
        ))}
      </div>

      {Object.keys(estimate.languages).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(estimate.languages).map(([lang, count]) => (
            <span
              key={lang}
              className="rounded-full border border-slate-600/50 bg-slate-800/50 px-3 py-1 text-xs text-slate-300"
            >
              {lang} · {count}
            </span>
          ))}
        </div>
      )}

      {estimate.warnings.length > 0 && (
        <ul className="space-y-1 text-sm text-amber-300/90">
          {estimate.warnings.map((w) => (
            <li key={w}>⚠ {w}</li>
          ))}
        </ul>
      )}

      {hasGaps && (
        <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-4">
          <p className="text-sm text-slate-300">
            {unsupportedList.length > 0
              ? `Found ${unsupportedList.length} unsupported file type(s) in this repo.`
              : "No ingestible source files were detected for supported languages."}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Tell us what legacy language you need — we review every request.
          </p>
          <LanguageRequestForm
            defaultOpen
            defaultExtensions={defaultExtensions}
            defaultMessage={
              unsupportedList.length > 0
                ? `Please add support for extensions: ${defaultExtensions} (repo: ${owner}/${name})`
                : `Please add support for source files in ${owner}/${name}`
            }
          />
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onConfirm}
          disabled={confirming || estimate.file_count === 0}
          className="flex-1 rounded-xl bg-amber-500 px-4 py-3 text-sm font-semibold text-slate-900 transition hover:bg-amber-400 disabled:opacity-60"
        >
          {confirming ? "Starting ingest…" : "Confirm & start ingestion"}
        </button>
        <button
          onClick={onCancel}
          className="rounded-xl border border-slate-600 px-4 py-3 text-sm text-slate-400 transition hover:border-slate-500 hover:text-slate-200"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
