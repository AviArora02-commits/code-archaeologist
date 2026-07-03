"use client";

import { useState } from "react";
import type { ConnectResponse } from "@/lib/api";
import { api } from "@/lib/api";

interface Props {
  onConnected: (data: ConnectResponse) => void;
}

export function ConnectForm({ onConnected }: Props) {
  const [url, setUrl] = useState("");
  const [subfolder, setSubfolder] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.connect(url, subfolder || undefined, token || undefined);
      onConnected(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="mb-2 block text-xs font-medium uppercase tracking-widest text-slate-400">
          GitHub Repository URL
        </label>
        <input
          type="url"
          required
          placeholder="https://github.com/owner/repo"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="w-full rounded-xl border border-slate-700/60 bg-slate-900/50 px-4 py-3.5 text-sm text-slate-100 outline-none transition focus:border-sky-500/50 focus:ring-2 focus:ring-sky-500/20"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-2 block text-xs font-medium uppercase tracking-widest text-slate-400">
            Subfolder (optional)
          </label>
          <input
            type="text"
            placeholder="src/lib"
            value={subfolder}
            onChange={(e) => setSubfolder(e.target.value)}
            className="w-full rounded-xl border border-slate-700/60 bg-slate-900/50 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-sky-500/50"
          />
        </div>
        <div>
          <label className="mb-2 block text-xs font-medium uppercase tracking-widest text-slate-400">
            GitHub PAT (optional)
          </label>
          <input
            type="password"
            placeholder="ghp_…"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="w-full rounded-xl border border-slate-700/60 bg-slate-900/50 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-sky-500/50"
          />
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="group relative w-full overflow-hidden rounded-xl bg-gradient-to-r from-sky-600 to-cyan-500 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-sky-900/40 transition hover:shadow-sky-800/50 disabled:opacity-60"
      >
        <span className="relative z-10">
          {loading ? "Analyzing repository…" : "Connect & estimate ingest"}
        </span>
      </button>
    </form>
  );
}
