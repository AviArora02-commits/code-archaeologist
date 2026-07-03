"use client";

import type { JobStatus } from "@/lib/api";

interface Props {
  job: JobStatus;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "text-slate-400",
  queued: "text-sky-400",
  running: "text-sky-300",
  completed: "text-emerald-400",
  failed: "text-red-400",
};

export function IngestProgress({ job }: Props) {
  const pct =
    job.total_files > 0 ? Math.round((job.files_processed / job.total_files) * 100) : 0;
  const isActive = ["pending", "queued", "running"].includes(job.status);

  return (
    <div className="animate-fade-up space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">Ingestion</p>
          <p className={`text-sm font-medium ${STATUS_COLORS[job.status] ?? "text-slate-300"}`}>
            {job.status}
            {job.cognee_status && (
              <span className="ml-2 text-slate-500">· Cognee: {job.cognee_status}</span>
            )}
          </p>
        </div>
        {job.total_files > 0 && (
          <span className="font-mono text-sm text-slate-400">
            {job.files_processed}/{job.total_files}
          </span>
        )}
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            job.status === "completed"
              ? "bg-emerald-500"
              : job.status === "failed"
                ? "bg-red-500"
                : "bg-gradient-to-r from-sky-600 to-cyan-400"
          }`}
          style={{ width: `${job.status === "completed" ? 100 : pct}%` }}
        />
      </div>

      {job.progress_message && (
        <p className={`text-sm text-slate-400 ${isActive ? "animate-pulse-glow" : ""}`}>
          {job.progress_message}
        </p>
      )}

      {isActive && job.files_processed >= job.total_files && job.total_files > 0 && (
        <p className="text-xs text-slate-500">
          Cognee Cloud indexes each file with an LLM call — this can take 1–3 minutes per file.
        </p>
      )}

      {job.error_message && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {job.error_message}
        </p>
      )}
    </div>
  );
}
