"""Pydantic API models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ConnectRepoRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL")
    subfolder: str | None = Field(default=None, description="Optional subfolder to scope ingestion")
    github_token: str | None = Field(default=None, description="Optional PAT for higher rate limits")


class DryRunEstimate(BaseModel):
    file_count: int
    chunk_count: int
    estimated_llm_calls: int
    estimated_cost_usd: float
    skipped_files: int
    languages: dict[str, int]
    unsupported_extensions: dict[str, int] = Field(default_factory=dict)
    supported_language_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class ConnectRepoResponse(BaseModel):
    repo_id: str
    owner: str
    name: str
    dataset_name: str
    job_id: str
    dry_run: DryRunEstimate


class ConfirmIngestRequest(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    repo_id: str
    status: str
    progress_message: str | None
    files_processed: int
    total_files: int
    cognee_status: str | None = None
    error_message: str | None = None
    dry_run: DryRunEstimate | None = None


class RepoSummary(BaseModel):
    id: str
    owner: str
    name: str
    url: str
    dataset_name: str
    latest_job_status: str | None = None


class EvidenceItem(BaseModel):
    kind: Literal["code", "commit", "pull_request", "issue", "author", "text"]
    label: str
    url: str | None = None
    sha: str | None = None
    number: int | None = None
    snippet: str | None = None


class WhyQueryRequest(BaseModel):
    repo_id: str
    question: str = Field(..., min_length=3)


class WhyQueryResponse(BaseModel):
    answer: str
    evidence_chain: list[EvidenceItem]
    raw_sources: list[dict[str, Any]] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    repo_id: str
    query: str
    answer: str
    score: Literal[-1, 1]


class LanguageInfo(BaseModel):
    id: str
    label: str
    extensions: list[str]


class LanguageRequestBody(BaseModel):
    language_name: str = Field(..., min_length=2, max_length=120)
    message: str = Field(..., min_length=10, max_length=2000)
    file_extensions: str | None = Field(default=None, max_length=200)
    repo_url: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(default=None, max_length=200)


class ExpertKnowledgeBody(BaseModel):
    author_name: str = Field(..., min_length=2, max_length=120)
    topic: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=20, max_length=8000)
    related_file: str | None = Field(default=None, max_length=500)
    related_symbol: str | None = Field(default=None, max_length=200)


class ExpertKnowledgeItem(BaseModel):
    id: str
    author_name: str
    topic: str
    content: str
    related_file: str | None = None
    related_symbol: str | None = None
    cognee_stored: bool = False
    created_at: str


class GraphNode(BaseModel):
    id: str
    label: str
    kind: str
    detail: str | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str


class KnowledgeGraphResponse(BaseModel):
    repo_id: str
    dataset_name: str
    cognee_dataset_id: str | None = None
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: dict[str, Any] = Field(default_factory=dict)


class MemorySummary(BaseModel):
    repo_count: int
    datasets: list[str]
    message: str


class RepoMemoryCard(BaseModel):
    id: str
    owner: str
    name: str
    url: str
    dataset_name: str
    cognee_dataset_id: str | None = None
    job_status: str | None = None
    files_indexed: int = 0
    total_files: int = 0
    memory_nodes: int = 0
    expert_entries: int = 0
    cognee_persisted: bool = False


class MemoryDashboardResponse(BaseModel):
    repo_count: int
    total_memory_nodes: int
    total_expert_entries: int
    cognee_mode: str
    repos: list[RepoMemoryCard]
    cognee_lifecycle: dict[str, str] = Field(default_factory=dict)
    message: str = ""
