"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { parseApiError } from "@/lib/errors";

interface Props {
  defaultOpen?: boolean;
  defaultLanguage?: string;
  defaultExtensions?: string;
  defaultMessage?: string;
  defaultRepoUrl?: string;
}

export function LanguageRequestForm({
  defaultOpen = false,
  defaultLanguage = "",
  defaultExtensions = "",
  defaultMessage = "",
  defaultRepoUrl = "",
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [language, setLanguage] = useState(defaultLanguage);
  const [extensions, setExtensions] = useState(defaultExtensions);
  const [repoUrl, setRepoUrl] = useState(defaultRepoUrl);
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState(defaultMessage);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.requestLanguage({
        language_name: language,
        message,
        file_extensions: extensions || undefined,
        repo_url: repoUrl || undefined,
        contact_email: email || undefined,
      });
      setStatus(
        `Request received (ref ${res.request_id.slice(0, 8)}). We review legacy language requests regularly.`
      );
      setLanguage("");
      setExtensions("");
      setMessage("");
    } catch (err) {
      setError(parseApiError(err instanceof Error ? err.message : "Request failed"));
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-3 text-xs text-sky-400/80 underline-offset-2 hover:text-sky-300 hover:underline"
      >
        Missing a legacy language? Request it →
      </button>
    );
  }

  return (
    <form
      onSubmit={submit}
      className="mt-4 space-y-3 rounded-xl border border-slate-700/50 bg-slate-900/40 p-4"
    >
      <p className="text-xs font-medium uppercase tracking-widest text-slate-400">
        Request a language
      </p>
      <input
        required
        placeholder="Language name (e.g. NATURAL, Focus, CA-Telon)"
        value={language}
        onChange={(e) => setLanguage(e.target.value)}
        className="w-full rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm text-slate-100"
      />
      <input
        placeholder="File extensions (e.g. .nsn, .foc)"
        value={extensions}
        onChange={(e) => setExtensions(e.target.value)}
        className="w-full rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm text-slate-100"
      />
      <input
        placeholder="Example repo URL (optional)"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
        className="w-full rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm text-slate-100"
      />
      <input
        placeholder="Your email (optional, for follow-up)"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm text-slate-100"
      />
      <textarea
        required
        minLength={10}
        placeholder="Why do you need this language? Sample files or use case…"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={3}
        className="w-full rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2 text-sm text-slate-100"
      />
      {error && <p className="text-xs text-red-300">{error}</p>}
      {status && <p className="text-xs text-emerald-300">{status}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-sky-600 px-4 py-2 text-xs font-medium text-white disabled:opacity-60"
        >
          {loading ? "Sending…" : "Send request to team"}
        </button>
        {!defaultOpen && (
          <button type="button" onClick={() => setOpen(false)} className="text-xs text-slate-500">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
