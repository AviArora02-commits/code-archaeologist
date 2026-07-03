"use client";

import type { RepoSummary } from "@/lib/api";

interface Props {
  repos: RepoSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function RepoSidebar({ repos, selectedId, onSelect, onDelete }: Props) {
  if (repos.length === 0) {
    return (
      <p className="text-sm text-slate-500">No repositories connected yet.</p>
    );
  }

  return (
    <ul className="space-y-2">
      {repos.map((repo) => {
        const active = repo.id === selectedId;
        return (
          <li key={repo.id}>
            <button
              onClick={() => onSelect(repo.id)}
              className={`group w-full rounded-xl border px-4 py-3 text-left transition ${
                active
                  ? "border-sky-500/40 bg-sky-500/10"
                  : "border-transparent bg-slate-800/30 hover:border-slate-700/50 hover:bg-slate-800/50"
              }`}
            >
              <p className="font-medium text-slate-200">
                {repo.owner}/{repo.name}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                {repo.latest_job_status ?? "no jobs"}
              </p>
            </button>
            {active && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(`Delete memory for ${repo.owner}/${repo.name}?`)) {
                    onDelete(repo.id);
                  }
                }}
                className="mt-1 w-full text-left text-xs text-red-400/70 transition hover:text-red-400"
              >
                Delete memory
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
