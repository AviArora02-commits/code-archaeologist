const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export interface DryRunEstimate {
  file_count: number;
  chunk_count: number;
  estimated_llm_calls: number;
  estimated_cost_usd: number;
  skipped_files: number;
  languages: Record<string, number>;
  unsupported_extensions?: Record<string, number>;
  supported_language_count?: number;
  warnings: string[];
}

export interface LanguageInfo {
  id: string;
  label: string;
  extensions: string[];
}

export interface ExpertKnowledgeItem {
  id: string;
  author_name: string;
  topic: string;
  content: string;
  related_file?: string | null;
  related_symbol?: string | null;
  cognee_stored: boolean;
  created_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  kind: string;
  detail?: string | null;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  kind: string;
}

export interface KnowledgeGraph {
  repo_id: string;
  dataset_name: string;
  cognee_dataset_id?: string | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_nodes?: number;
    total_edges?: number;
    by_kind?: Record<string, number>;
    persisted_in_cognee?: boolean;
  };
}

export interface RepoMemoryCard {
  id: string;
  owner: string;
  name: string;
  url: string;
  dataset_name: string;
  cognee_dataset_id?: string | null;
  job_status?: string | null;
  files_indexed: number;
  total_files: number;
  memory_nodes: number;
  expert_entries: number;
  cognee_persisted: boolean;
}

export interface MemoryDashboard {
  repo_count: number;
  total_memory_nodes: number;
  total_expert_entries: number;
  cognee_mode: string;
  repos: RepoMemoryCard[];
  cognee_lifecycle: Record<string, string>;
  message: string;
}

export interface ConnectResponse {
  repo_id: string;
  owner: string;
  name: string;
  dataset_name: string;
  job_id: string;
  dry_run: DryRunEstimate;
}

export interface JobStatus {
  job_id: string;
  repo_id: string;
  status: string;
  progress_message: string | null;
  files_processed: number;
  total_files: number;
  cognee_status: string | null;
  error_message: string | null;
  dry_run: DryRunEstimate | null;
}

export interface EvidenceItem {
  kind: string;
  label: string;
  url: string | null;
  sha?: string | null;
  number?: number | null;
  snippet?: string | null;
}

export interface WhyResponse {
  answer: string;
  evidence_chain: EvidenceItem[];
}

export interface RepoSummary {
  id: string;
  owner: string;
  name: string;
  url: string;
  dataset_name: string;
  latest_job_status: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  connect: (url: string, subfolder?: string, githubToken?: string) =>
    request<ConnectResponse>("/repos/connect", {
      method: "POST",
      body: JSON.stringify({ url, subfolder, github_token: githubToken }),
    }),
  confirmIngest: (repoId: string, jobId: string) =>
    request<{ status: string }>(`/repos/${repoId}/ingest`, {
      method: "POST",
      body: JSON.stringify({ job_id: jobId }),
    }),
  jobStatus: (jobId: string) => request<JobStatus>(`/jobs/${jobId}`),
  listRepos: () => request<RepoSummary[]>("/repos"),
  why: (repoId: string, question: string) =>
    request<WhyResponse>("/query/why", {
      method: "POST",
      body: JSON.stringify({ repo_id: repoId, question }),
    }),
  deleteRepo: (repoId: string) =>
    request<{ status: string }>(`/repos/${repoId}`, { method: "DELETE" }),
  feedback: (repoId: string, query: string, answer: string, score: 1 | -1) =>
    request<{ status: string }>("/feedback", {
      method: "POST",
      body: JSON.stringify({ repo_id: repoId, query, answer, score }),
    }),
  requestLanguage: (body: {
    language_name: string;
    message: string;
    file_extensions?: string;
    repo_url?: string;
    contact_email?: string;
  }) =>
    request<{ status: string; request_id: string }>("/languages/request", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  supportedLanguages: () =>
    request<{ id: string; label: string; extensions: string[] }[]>("/languages/supported"),
  repoGraph: (repoId: string) => request<KnowledgeGraph>(`/repos/${repoId}/graph`),
  listExpertKnowledge: (repoId: string) =>
    request<ExpertKnowledgeItem[]>(`/repos/${repoId}/expert-knowledge`),
  addExpertKnowledge: (
    repoId: string,
    body: {
      author_name: string;
      topic: string;
      content: string;
      related_file?: string;
      related_symbol?: string;
    }
  ) =>
    request<ExpertKnowledgeItem>(`/repos/${repoId}/expert-knowledge`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  memorySummary: () =>
    request<{ repo_count: number; datasets: string[]; message: string }>("/memory/summary"),
  memoryDashboard: () => request<MemoryDashboard>("/memory/dashboard"),
};
