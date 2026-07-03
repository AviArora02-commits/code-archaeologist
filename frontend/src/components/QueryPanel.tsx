"use client";

import { useState } from "react";
import { parseApiError } from "@/lib/errors";
import type { WhyResponse } from "@/lib/api";
import { api } from "@/lib/api";
import { AnswerView } from "@/components/AnswerView";
import { EvidenceChain } from "./EvidenceChain";

interface Props {
  repoId: string;
  repoName: string;
  disabled?: boolean;
}

export function QueryPanel({ repoId, repoName, disabled }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WhyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  async function sendFeedback(score: 1 | -1) {
    if (!result) return;
    setFeedbackMsg(null);
    try {
      await api.feedback(repoId, question, result.answer, score);
      setFeedbackMsg(
        score === 1
          ? "Thanks — Cognee improve() will refine this dataset."
          : "Feedback recorded."
      );
    } catch {
      setFeedbackMsg("Could not send feedback.");
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.why(repoId, question);
      setResult(data);
    } catch (err) {
      const raw = err instanceof Error ? err.message : "Query failed";
      setError(parseApiError(raw));
    } finally {
      setLoading(false);
    }
  }

  const examples = [
    `Why does the main function in ${repoName} work this way?`,
    "What commit introduced this pattern?",
    "Which PR or issue motivated this change?",
  ];

  return (
    <div className="space-y-6">
      <form onSubmit={handleAsk} className="space-y-4">
        <label className="block text-xs font-medium uppercase tracking-widest text-slate-400">
          Ask why
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={disabled || loading}
            placeholder="Why does X do Y?"
            className="flex-1 rounded-xl border border-slate-700/60 bg-slate-900/50 px-4 py-3.5 text-sm text-slate-100 outline-none transition focus:border-sky-500/50 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={disabled || loading || !question.trim()}
            className="shrink-0 rounded-xl border border-sky-500/40 bg-sky-500/10 px-6 py-3.5 text-sm font-medium text-sky-300 transition hover:bg-sky-500/20 disabled:opacity-50"
          >
            {loading ? "Tracing…" : "Trace"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {examples.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setQuestion(ex)}
              className="rounded-full border border-slate-700/50 px-3 py-1 text-xs text-slate-500 transition hover:border-slate-600 hover:text-slate-300"
            >
              {ex}
            </button>
          ))}
        </div>
      </form>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {result && (
        <div className="animate-fade-up space-y-6">
            <div className="rounded-xl border border-slate-700/40 bg-slate-900/30 p-5">
            <p className="mb-3 text-xs uppercase tracking-widest text-sky-400/80">Answer</p>
            <AnswerView text={result.answer} />
          </div>

          <div>
            <p className="mb-4 text-xs uppercase tracking-widest text-slate-500">Evidence chain</p>
            <EvidenceChain items={result.evidence_chain} />
          </div>

          <div className="flex items-center gap-3 border-t border-slate-800/60 pt-4">
            <span className="text-xs text-slate-500">Was this helpful?</span>
            <button
              type="button"
              onClick={() => void sendFeedback(1)}
              className="rounded-lg border border-emerald-500/30 px-3 py-1 text-xs text-emerald-300 hover:bg-emerald-500/10"
            >
              👍 Yes — improve memory
            </button>
            <button
              type="button"
              onClick={() => void sendFeedback(-1)}
              className="rounded-lg border border-slate-600/50 px-3 py-1 text-xs text-slate-400 hover:bg-slate-800/50"
            >
              👎 No
            </button>
            {feedbackMsg && <span className="text-xs text-slate-500">{feedbackMsg}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
