"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ExpertKnowledgeItem } from "@/lib/api";
import { parseApiError } from "@/lib/errors";

interface Props {
  repoId: string;
}

export function ExpertKnowledgePanel({ repoId }: Props) {
  const [open, setOpen] = useState(false);
  const [author, setAuthor] = useState("");
  const [topic, setTopic] = useState("");
  const [content, setContent] = useState("");
  const [relatedFile, setRelatedFile] = useState("");
  const [relatedSymbol, setRelatedSymbol] = useState("");
  const [items, setItems] = useState<ExpertKnowledgeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    api.listExpertKnowledge(repoId).then(setItems).catch(() => setItems([]));
  }, [repoId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const row = await api.addExpertKnowledge(repoId, {
        author_name: author,
        topic,
        content,
        related_file: relatedFile || undefined,
        related_symbol: relatedSymbol || undefined,
      });
      setItems((prev) => [row, ...prev]);
      setStatus(
        row.cognee_stored
          ? "Saved to Cognee memory — Trace will use this expert knowledge."
          : "Saved locally. Cognee sync pending; try again if queries miss this context."
      );
      setTopic("");
      setContent("");
      setRelatedFile("");
      setRelatedSymbol("");
    } catch (err) {
      setError(parseApiError(err instanceof Error ? err.message : "Save failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-fuchsia-500/20 bg-fuchsia-500/5 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-fuchsia-400/80">
            Expert knowledge
          </p>
          <p className="mt-1 text-sm text-slate-400">
            Legacy systems live in people&apos;s heads. Teach the graph what Gemini cannot know.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 rounded-lg border border-fuchsia-500/30 px-3 py-1.5 text-xs text-fuchsia-300"
        >
          {open ? "Close" : "+ Add knowledge"}
        </button>
      </div>

      {open && (
        <form onSubmit={submit} className="mt-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              required
              placeholder="Your name"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              className="rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm"
            />
            <input
              required
              placeholder="Topic (e.g. nightly batch job flow)"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm"
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              placeholder="Related file (optional)"
              value={relatedFile}
              onChange={(e) => setRelatedFile(e.target.value)}
              className="rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm"
            />
            <input
              placeholder="Related symbol (optional)"
              value={relatedSymbol}
              onChange={(e) => setRelatedSymbol(e.target.value)}
              className="rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm"
            />
          </div>
          <textarea
            required
            minLength={20}
            rows={5}
            placeholder="Explain how this repo or subsystem actually works — business rules, quirks, ops context…"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm"
          />
          {error && <p className="text-xs text-red-300">{error}</p>}
          {status && <p className="text-xs text-emerald-300">{status}</p>}
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-fuchsia-600 px-4 py-2 text-xs font-medium text-white disabled:opacity-60"
          >
            {loading ? "Saving to memory…" : "Save to Cognee memory"}
          </button>
        </form>
      )}

      {items.length > 0 && (
        <ul className="mt-4 space-y-2">
          {items.slice(0, 5).map((item) => (
            <li
              key={item.id}
              className="rounded-lg border border-slate-700/40 bg-slate-900/30 px-3 py-2 text-xs"
            >
              <p className="font-medium text-slate-200">{item.topic}</p>
              <p className="text-slate-500">
                {item.author_name}
                {item.cognee_stored ? " · in Cognee" : " · local only"}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
