"""API route handlers."""

from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.db import Database
from app.languages import supported_language_list
from app.models.schemas import (
    ConfirmIngestRequest,
    ConnectRepoRequest,
    ConnectRepoResponse,
    DryRunEstimate,
    ExpertKnowledgeBody,
    ExpertKnowledgeItem,
    FeedbackRequest,
    JobStatusResponse,
    KnowledgeGraphResponse,
    LanguageInfo,
    LanguageRequestBody,
    MemoryDashboardResponse,
    MemorySummary,
    RepoSummary,
    WhyQueryRequest,
    WhyQueryResponse,
)
from app.services import cognee_service
from app.services.expert_service import ExpertService
from app.services.graph_service import GraphService
from app.services.ingest_service import IngestService
from app.services.memory_dashboard_service import MemoryDashboardService
from app.services.notification_service import notify_expert_knowledge_submitted
from app.services.query_service import QueryService

router = APIRouter()
db = Database()
ingest_service = IngestService(db)
query_service = QueryService(db)
expert_service = ExpertService(db)
graph_service = GraphService(db)
memory_dashboard = MemoryDashboardService(db)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/repos/connect", response_model=ConnectRepoResponse)
async def connect_repo(body: ConnectRepoRequest) -> ConnectRepoResponse:
    try:
        result, dry_run = await ingest_service.dry_run(
            body.url, body.subfolder, body.github_token
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    repo = result["repo"]
    job = result["job"]
    return ConnectRepoResponse(
        repo_id=repo["id"],
        owner=repo["owner"],
        name=repo["name"],
        dataset_name=repo["dataset_name"],
        job_id=job["id"],
        dry_run=dry_run,
    )


@router.post("/repos/{repo_id}/ingest")
async def confirm_ingest(
    repo_id: str, body: ConfirmIngestRequest, background_tasks: BackgroundTasks
) -> dict[str, str]:
    job = await db.get_job(body.job_id)
    if not job or job["repo_id"] != repo_id:
        raise HTTPException(status_code=404, detail="Job not found for this repo")
    await db.update_job(body.job_id, status="queued", confirmed=1, progress_message="Confirmed")
    background_tasks.add_task(ingest_service.run_ingestion, body.job_id)
    return {"status": "queued", "job_id": body.job_id}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    cognee_status = None
    repo = await db.get_repo(job["repo_id"])
    if repo and repo.get("cognee_dataset_id"):
        try:
            cognee_status = await cognee_service.get_dataset_status(repo["cognee_dataset_id"])
        except Exception:
            cognee_status = None

    dry_run = None
    if job.get("dry_run_estimate"):
        raw = job["dry_run_estimate"]
        if isinstance(raw, str):
            dry_run = DryRunEstimate(**json.loads(raw))
        else:
            dry_run = DryRunEstimate(**raw)

    return JobStatusResponse(
        job_id=job["id"],
        repo_id=job["repo_id"],
        status=job["status"],
        progress_message=job.get("progress_message"),
        files_processed=job.get("files_processed", 0),
        total_files=job.get("total_files", 0),
        cognee_status=cognee_status,
        error_message=job.get("error_message"),
        dry_run=dry_run,
    )


@router.get("/repos", response_model=list[RepoSummary])
async def list_repos() -> list[RepoSummary]:
    repos = await db.list_repos()
    summaries: list[RepoSummary] = []
    for repo in repos:
        job = await db.get_latest_job(repo["id"])
        summaries.append(
            RepoSummary(
                id=repo["id"],
                owner=repo["owner"],
                name=repo["name"],
                url=repo["url"],
                dataset_name=repo["dataset_name"],
                latest_job_status=job["status"] if job else None,
            )
        )
    return summaries


@router.post("/query/why", response_model=WhyQueryResponse)
async def why_query(body: WhyQueryRequest) -> WhyQueryResponse:
    try:
        return await query_service.ask_why(body.repo_id, body.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


@router.delete("/repos/{repo_id}")
async def delete_repo(repo_id: str) -> dict[str, str]:
    repo = await db.get_repo(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        await cognee_service.init_cognee()
        await cognee_service.forget_dataset(repo["dataset_name"])
    except Exception:
        pass
    await db.delete_repo(repo_id)
    return {"status": "deleted"}


@router.get("/languages/supported", response_model=list[LanguageInfo])
async def list_supported_languages() -> list[LanguageInfo]:
    return [LanguageInfo(**item) for item in supported_language_list()]


@router.post("/languages/request")
async def request_language(body: LanguageRequestBody) -> dict[str, str]:
    row = await db.create_language_request(
        language_name=body.language_name.strip(),
        message=body.message.strip(),
        file_extensions=body.file_extensions,
        repo_url=body.repo_url,
        contact_email=body.contact_email,
    )
    return {"status": "received", "request_id": row["id"]}


@router.get("/memory/dashboard", response_model=MemoryDashboardResponse)
async def memory_dashboard_view() -> MemoryDashboardResponse:
    return await memory_dashboard.get_dashboard()


@router.get("/memory/summary", response_model=MemorySummary)
async def memory_summary() -> MemorySummary:
    repos = await db.list_repos()
    datasets = [r["dataset_name"] for r in repos]
    return MemorySummary(
        repo_count=len(repos),
        datasets=datasets,
        message=(
            "Each repository is stored in its own Cognee dataset on Cognee Cloud. "
            "Datasets persist independently — connect up to many repos and each keeps "
            "its memory until you delete it."
        ),
    )


@router.get("/repos/{repo_id}/graph", response_model=KnowledgeGraphResponse)
async def repo_graph(repo_id: str) -> KnowledgeGraphResponse:
    try:
        return await graph_service.get_repo_graph(repo_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/repos/{repo_id}/expert-knowledge", response_model=list[ExpertKnowledgeItem])
async def list_expert_knowledge(repo_id: str) -> list[ExpertKnowledgeItem]:
    rows = await expert_service.list_knowledge(repo_id)
    return [
        ExpertKnowledgeItem(
            id=r["id"],
            author_name=r["author_name"],
            topic=r["topic"],
            content=r["content"],
            related_file=r.get("related_file"),
            related_symbol=r.get("related_symbol"),
            cognee_stored=bool(r.get("cognee_stored")),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/repos/{repo_id}/expert-knowledge", response_model=ExpertKnowledgeItem)
async def add_expert_knowledge(
    repo_id: str,
    body: ExpertKnowledgeBody,
    background_tasks: BackgroundTasks,
) -> ExpertKnowledgeItem:
    repo = await db.get_repo(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        row = await expert_service.add_knowledge(
            repo_id,
            author_name=body.author_name,
            topic=body.topic,
            content=body.content,
            related_file=body.related_file,
            related_symbol=body.related_symbol,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(notify_expert_knowledge_submitted, repo, row)

    return ExpertKnowledgeItem(
        id=row["id"],
        author_name=row["author_name"],
        topic=row["topic"],
        content=row["content"],
        related_file=row.get("related_file"),
        related_symbol=row.get("related_symbol"),
        cognee_stored=bool(row.get("cognee_stored")),
        created_at=row["created_at"],
    )


@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest) -> dict[str, str]:
    await db.add_feedback(body.repo_id, body.query, body.answer, body.score)
    try:
        await cognee_service.init_cognee()
        import cognee

        await cognee.improve()
    except Exception:
        pass
    return {"status": "recorded"}
