"use client";

import { useCallback, useEffect, useState } from "react";
import type { MemoryDashboard } from "@/lib/api";
import { api } from "@/lib/api";

interface Props {
  onSelectRepo?: (repoId: string) => void;
  selectedId?: string | null;
}

export function MemoryDashboardPanel({ onSelectRepo, selectedId }: Props) {
  const [data, setData] = useState<MemoryDashboard | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.memoryDashboard());
    } catch {
      setData(null);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 15000);
    return () => clearInterval(id);
  }, [load]);

  if (!data) {
    return (
      <p className="text-xs text-slate-500">Loading Cognee memory overview…</p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-widest text-slate-500">
          Memory fleet
        </p>
        <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-2 py-0.5 text-[10px] text-sky-300">
          {data.cognee_mode} mode
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        {[
          { label: "Repos", value: data.repo_count },
          { label: "Nodes", value: data.total_memory_nodes },
          { label: "Experts", value: data.total_expert_entries },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border border-slate-700/40 bg-slate-900/40 py-2">
            <p className="font-mono text-lg text-slate-100">{s.value}</p>
            <p className="text-[10px] text-slate-500">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        {data.repos.length === 0 && (
          <p className="text-xs text-slate-500">No datasets yet — connect a repo.</p>
        )}
        {data.repos.map((repo) => (
          <button
            key={repo.id}
            type="button"
            onClick={() => onSelectRepo?.(repo.id)}
            className={`w-full rounded-xl border px-3 py-2 text-left transition ${
              selectedId === repo.id
                ? "border-sky-500/50 bg-sky-500/10"
                : "border-slate-700/40 bg-slate-900/30 hover:border-slate-600"
            }`}
          >
            <p className="truncate text-sm font-medium text-slate-200">
              {repo.owner}/{repo.name}
            </p>
            <p className="truncate font-mono text-[10px] text-slate-500">{repo.dataset_name}</p>
            <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-slate-500">
              <span>{repo.job_status ?? "—"}</span>
              <span>·</span>
              <span>
                {repo.files_indexed}/{repo.total_files} files
              </span>
              <span>·</span>
              <span>{repo.memory_nodes} nodes</span>
              {repo.cognee_persisted && (
                <span className="text-emerald-400">· Cognee ✓</span>
              )}
            </div>
          </button>
        ))}
      </div>

      <CogneeLifecycle lifecycle={data.cognee_lifecycle} />
    </div>
  );
}

function CogneeLifecycle({ lifecycle }: { lifecycle: Record<string, string> }) {
  const ops = ["remember", "recall", "improve", "forget"] as const;
  const colors: Record<string, string> = {
    remember: "border-violet-500/40 text-violet-300",
    recall: "border-sky-500/40 text-sky-300",
    improve: "border-amber-500/40 text-amber-300",
    forget: "border-rose-500/40 text-rose-300",
  };

  return (
    <div className="rounded-xl border border-slate-700/30 bg-slate-950/40 p-3">
      <p className="mb-2 text-[10px] uppercase tracking-widest text-slate-500">
        Cognee lifecycle
      </p>
      <div className="space-y-1.5">
        {ops.map((op) => (
          <div key={op} className="flex gap-2 text-[10px]">
            <code className={`shrink-0 rounded border px-1.5 py-0.5 font-mono ${colors[op]}`}>
              {op}()
            </code>
            <span className="text-slate-500">{lifecycle[op]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
