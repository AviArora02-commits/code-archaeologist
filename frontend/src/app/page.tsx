"use client";

import { useCallback, useEffect, useState } from "react";
import { ConnectForm } from "@/components/ConnectForm";
import { LanguageRequestForm } from "@/components/LanguageRequestForm";
import { SupportedLanguagesPanel } from "@/components/SupportedLanguagesPanel";
import { DryRunPanel } from "@/components/DryRunPanel";
import { IngestProgress } from "@/components/IngestProgress";
import { ExpertKnowledgePanel } from "@/components/ExpertKnowledgePanel";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { QueryPanel } from "@/components/QueryPanel";
import { MemoryDashboardPanel } from "@/components/MemoryDashboardPanel";
import { RepoSidebar } from "@/components/RepoSidebar";
import type { ConnectResponse, JobStatus, RepoSummary } from "@/lib/api";
import { api } from "@/lib/api";

type Phase = "connect" | "dry-run" | "ingesting" | "ready";

export default function Home() {
  const [repos, setRepos] = useState<RepoSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("connect");
  const [pending, setPending] = useState<ConnectResponse | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [confirming, setConfirming] = useState(false);

  const loadRepos = useCallback(async () => {
    try {
      const list = await api.listRepos();
      setRepos(list);
      setSelectedId((current) => {
        if (current && list.some((r) => r.id === current)) return current;
        return list[0]?.id ?? null;
      });
    } catch {
      /* backend may be offline during dev */
    }
  }, []);

  useEffect(() => {
    loadRepos();
    const onFocus = () => loadRepos();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [loadRepos]);

  useEffect(() => {
    if (!job || !["queued", "running", "pending"].includes(job.status)) return;
    const interval = setInterval(async () => {
      try {
        const updated = await api.jobStatus(job.job_id);
        setJob(updated);
        if (updated.status === "completed") {
          setPhase("ready");
          loadRepos();
        } else if (updated.status === "failed") {
          setPhase("dry-run");
        }
      } catch {
        /* ignore poll errors */
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [job, loadRepos]);

  function handleConnected(data: ConnectResponse) {
    setPending(data);
    setPhase("dry-run");
    loadRepos();
    setSelectedId(data.repo_id);
  }

  async function handleConfirmIngest() {
    if (!pending) return;
    setConfirming(true);
    try {
      await api.confirmIngest(pending.repo_id, pending.job_id);
      const status = await api.jobStatus(pending.job_id);
      setJob(status);
      setPhase("ingesting");
    } finally {
      setConfirming(false);
    }
  }

  async function handleDelete(repoId: string) {
    await api.deleteRepo(repoId);
    setSelectedId(null);
    setPending(null);
    setJob(null);
    setPhase("connect");
    loadRepos();
  }

  const selected = repos.find((r) => r.id === selectedId);
  const isReady = selected?.latest_job_status === "completed" || phase === "ready";

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-slate-800/60">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-sky-500/30 bg-sky-500/10 font-mono text-sky-400">
              ⎇
            </div>
            <div>
              <h1 className="font-serif text-2xl tracking-tight text-slate-100">
                Code Archaeologist
              </h1>
              <p className="text-xs text-slate-500">
                function → commit → PR → issue
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-3 sm:flex">
            <a
              href={process.env.NEXT_PUBLIC_GITHUB_REPO ?? "https://github.com"}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-slate-500 hover:text-slate-300"
            >
              GitHub
            </a>
            <span className="rounded-full border border-slate-700/50 px-3 py-1 text-xs text-slate-500">
              Powered by Cognee
            </span>
          </div>
        </div>
        <div className="glow-line mx-auto max-w-7xl" />
      </header>

      <main className="mx-auto grid max-w-7xl gap-8 px-6 py-10 lg:grid-cols-[280px_1fr]">
        {/* Sidebar */}
        <aside className="glass rounded-2xl p-5">
          <p className="mb-4 text-xs font-medium uppercase tracking-widest text-slate-500">
            Repositories
          </p>
          <RepoSidebar
            repos={repos}
            selectedId={selectedId}
            onSelect={(id) => {
              setSelectedId(id);
              const r = repos.find((x) => x.id === id);
              if (r?.latest_job_status === "completed") setPhase("ready");
            }}
            onDelete={handleDelete}
          />
          <div className="mt-6 border-t border-slate-800/60 pt-5">
            <MemoryDashboardPanel
              selectedId={selectedId}
              onSelectRepo={(id) => {
                setSelectedId(id);
                const r = repos.find((x) => x.id === id);
                if (r?.latest_job_status === "completed") setPhase("ready");
              }}
            />
          </div>
        </aside>

        {/* Main panel */}
        <div className="space-y-6">
          {/* Hero when no active work */}
          {phase === "connect" && !selected && (
            <section className="glass animate-fade-up rounded-2xl p-8 lg:p-12">
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-sky-400/80">
                Trace the why behind your code
              </p>
              <h2 className="font-serif text-4xl leading-tight text-slate-100 lg:text-5xl">
                Not semantic search.
                <br />
                <span className="italic text-slate-400">Sourced evidence chains.</span>
              </h2>
              <p className="mt-4 max-w-xl text-sm leading-relaxed text-slate-400">
                Connect a GitHub repo, ingest its code history and PR/issue context into a
                Cognee knowledge graph, then ask why any function exists — with citations
                that link to real commits, pull requests, and issues.
              </p>
              <div className="mt-8 max-w-lg">
                <ConnectForm onConnected={handleConnected} />
                <SupportedLanguagesPanel />
                <LanguageRequestForm />
              </div>
            </section>
          )}

          {/* Connect form when repos exist but adding new */}
          {phase === "connect" && selected && (
            <section className="glass rounded-2xl p-8">
              <h2 className="mb-6 font-serif text-2xl text-slate-100">Connect another repo</h2>
              <ConnectForm onConnected={handleConnected} />
            </section>
          )}

          {phase === "dry-run" && pending && (
            <section className="glass rounded-2xl p-8">
              <DryRunPanel
                estimate={pending.dry_run}
                owner={pending.owner}
                name={pending.name}
                onConfirm={handleConfirmIngest}
                onCancel={() => setPhase("connect")}
                confirming={confirming}
              />
            </section>
          )}

          {phase === "ingesting" && job && (
            <section className="glass rounded-2xl p-8">
              <IngestProgress job={job} />
            </section>
          )}

          {(isReady || (selected && selected.latest_job_status === "completed")) && selected && (
            <section className="glass rounded-2xl p-8">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-widest text-emerald-400/80">Ready</p>
                  <h2 className="font-serif text-2xl text-slate-100">
                    {selected.owner}/{selected.name}
                  </h2>
                </div>
                <a
                  href={selected.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-sky-400 hover:underline"
                >
                  View on GitHub →
                </a>
              </div>
              <QueryPanel
                repoId={selected.id}
                repoName={selected.name}
                disabled={!isReady && selected.latest_job_status !== "completed"}
              />
              <div className="mt-8 space-y-8 border-t border-slate-800/60 pt-8">
                <ExpertKnowledgePanel repoId={selected.id} />
                <KnowledgeGraph repoId={selected.id} />
              </div>
            </section>
          )}

          {/* Add repo CTA when viewing completed repo */}
          {isReady && (
            <button
              onClick={() => setPhase("connect")}
              className="text-sm text-slate-500 transition hover:text-slate-300"
            >
              + Connect another repository
            </button>
          )}
        </div>
      </main>

      <footer className="border-t border-slate-800/40 py-6 text-center">
        <p className="text-xs text-slate-600">
          Built with Cognee graph memory · AI-assisted development disclosed in README
        </p>
        <div className="mt-3 flex justify-center">
          <LanguageRequestForm />
        </div>
      </footer>
    </div>
  );
}
