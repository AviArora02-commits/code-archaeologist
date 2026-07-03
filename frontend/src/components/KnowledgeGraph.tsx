"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { KnowledgeGraph as GraphData } from "@/lib/api";
import { api } from "@/lib/api";

const KIND_COLORS: Record<string, string> = {
  repo: "#38bdf8",
  file: "#a78bfa",
  entity: "#34d399",
  commit: "#fbbf24",
  expert: "#f472b6",
};

interface Props {
  repoId: string;
}

export function KnowledgeGraph({ repoId }: Props) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.repoGraph(repoId);
      setGraph(data);
      setError(null);
    } catch {
      setError("Could not load knowledge graph.");
    }
  }, [repoId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!graph || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = 320;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, w, h);
    const cx = w / 2;
    const cy = h / 2;
    const nodes = graph.nodes.slice(0, 48);
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const positions = new Map<string, { x: number; y: number }>();

    nodes.forEach((n, i) => {
      const angle = (i / Math.max(nodes.length, 1)) * Math.PI * 2;
      const ring = n.kind === "repo" ? 0 : n.kind === "expert" ? 0.35 : 0.65;
      const r = Math.min(w, h) * 0.38 * ring + (n.kind === "repo" ? 0 : 40);
      positions.set(n.id, {
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r,
      });
    });

    const repoNode = nodes.find((n) => n.kind === "repo");
    if (repoNode) positions.set(repoNode.id, { x: cx, y: cy });

    graph.edges.forEach((e) => {
      const a = positions.get(e.source);
      const b = positions.get(e.target);
      if (!a || !b || !nodeMap.has(e.source) || !nodeMap.has(e.target)) return;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = "rgba(100, 116, 139, 0.25)";
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    nodes.forEach((n) => {
      const p = positions.get(n.id);
      if (!p) return;
      const color = KIND_COLORS[n.kind] ?? "#94a3b8";
      ctx.beginPath();
      ctx.arc(p.x, p.y, n.kind === "repo" ? 10 : 6, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = "rgba(15, 23, 42, 0.8)";
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }, [graph]);

  if (error) {
    return <p className="text-xs text-slate-500">{error}</p>;
  }

  if (!graph) {
    return <p className="text-xs text-slate-500">Loading knowledge graph…</p>;
  }

  const kinds = Object.entries(graph.stats.by_kind ?? {});

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-widest text-violet-400/80">Knowledge graph</p>
        <div className="flex flex-wrap gap-2">
          {kinds.map(([kind, count]) => (
            <span
              key={kind}
              className="rounded-full border border-slate-700/50 px-2 py-0.5 text-[10px] text-slate-400"
              style={{ borderColor: `${KIND_COLORS[kind] ?? "#64748b"}55` }}
            >
              <span
                className="mr-1 inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: KIND_COLORS[kind] ?? "#64748b" }}
              />
              {kind} · {count}
            </span>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-700/40 bg-slate-950/50">
        <canvas ref={canvasRef} className="h-80 w-full" />
      </div>

      <p className="text-xs text-slate-500">
        {graph.stats.persisted_in_cognee
          ? `Persisted in Cognee Cloud as dataset "${graph.dataset_name}". Safe to add or remove repos independently.`
          : "Graph built from local memory index. Re-ingest to sync with Cognee Cloud."}
        {graph.nodes.length > 48 ? " Showing first 48 nodes for clarity." : ""}
      </p>

      <button
        type="button"
        onClick={() => void load()}
        className="text-xs text-sky-400 hover:underline"
      >
        Refresh graph
      </button>
    </div>
  );
}
