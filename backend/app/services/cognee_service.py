"""Cognee dual-mode integration (local | cloud)."""

from __future__ import annotations

from typing import Any

import structlog

from app.config import Settings, get_settings
from app.models.ontology import Author, CodeEntity, Commit, Issue, PullRequest
from app.services.git_service import CommitRecord, EntityHistory
from app.services.github_service import IssueRecord, PullRequestRecord

logger = structlog.get_logger()

_cognee_initialized = False


def _apply_llm_env(cfg: Settings) -> None:
    """Configure Cognee to use Gemini instead of OpenAI."""
    import os

    if cfg.gemini_api_key:
        os.environ["LLM_PROVIDER"] = cfg.llm_provider
        os.environ["LLM_API_KEY"] = cfg.gemini_api_key
        os.environ["LLM_MODEL"] = cfg.llm_model
    elif cfg.openai_api_key:
        os.environ.setdefault("LLM_PROVIDER", "openai")
        os.environ.setdefault("LLM_API_KEY", cfg.openai_api_key)


async def init_cognee(settings: Settings | None = None) -> None:
    """Initialize Cognee in local or cloud mode."""
    global _cognee_initialized
    if _cognee_initialized:
        return
    cfg = settings or get_settings()
    _apply_llm_env(cfg)
    import cognee

    if cfg.cognee_mode == "cloud":
        if not cfg.cognee_cloud_url or not cfg.cognee_api_key:
            raise RuntimeError("COGNEE_MODE=cloud requires COGNEE_CLOUD_URL and COGNEE_API_KEY")
        await cognee.serve(url=cfg.cognee_cloud_url, api_key=cfg.cognee_api_key)
        logger.info("cognee_cloud_connected", url=cfg.cognee_cloud_url)
    else:
        logger.info("cognee_local_mode")
    _cognee_initialized = True


def is_cloud_mode() -> bool:
    """True when SDK routes remember/recall to a remote Cognee instance."""
    try:
        from cognee.api.v1.serve.state import is_remote_mode

        return is_remote_mode()
    except Exception:
        return get_settings().cognee_mode == "cloud"


def parse_remember_result(result: Any) -> tuple[str | None, str, str | None]:
    """Extract dataset_id, status, and error from remember() output."""
    if isinstance(result, dict):
        dataset_id = result.get("dataset_id") or result.get("datasetId")
        return (
            str(dataset_id) if dataset_id else None,
            str(result.get("status", "unknown")),
            result.get("error"),
        )
    dataset_id = getattr(result, "dataset_id", None)
    return (
        str(dataset_id) if dataset_id else None,
        str(getattr(result, "status", "unknown")),
        getattr(result, "error", None),
    )


def _commit_node(record: CommitRecord) -> Commit:
    return Commit(
        sha=record.sha,
        message=record.message,
        timestamp=record.timestamp,
        url=record.url,
        author=Author(name=record.author_name, email=record.author_email),
    )


def _pr_node(record: PullRequestRecord, issues: list[IssueRecord]) -> PullRequest:
    return PullRequest(
        number=record.number,
        title=record.title,
        body=record.body,
        state=record.state,
        url=record.url,
        merged_at=record.merged_at,
        references=[
            Issue(number=i.number, title=i.title, body=i.body, state=i.state, url=i.url)
            for i in issues
        ],
    )


def entity_to_datapoint(
    entity: EntityHistory,
    prs: list[PullRequestRecord],
    issues: list[IssueRecord],
) -> CodeEntity:
    """Build a CodeEntity DataPoint with graph edges."""
    introduced = _commit_node(entity.introduced_commit) if entity.introduced_commit else None
    discussed = [_pr_node(pr, [i for i in issues if i.number in pr.issue_numbers]) for pr in prs]
    return CodeEntity(
        name=entity.entity_name,
        kind=entity.kind,
        file_path=entity.file_path,
        language=entity.language,
        signature=entity.signature,
        source_snippet=entity.source_snippet,
        introduced_in=introduced,
        discussed_in=discussed,
    )


def entity_to_document(
    entity: EntityHistory,
    prs: list[PullRequestRecord],
    issues: list[IssueRecord],
    owner: str,
    repo: str,
) -> str:
    """Structured text document for remember() when DataPoint path unavailable."""
    lines = [
        f"# CodeEntity: {entity.entity_name}",
        f"Kind: {entity.kind}",
        f"File: {entity.file_path}",
        f"Language: {entity.language}",
    ]
    if entity.signature:
        lines.append(f"Signature: {entity.signature}")
    if entity.source_snippet:
        lines.append(f"Source:\n{entity.source_snippet}")
    if entity.introduced_commit:
        c = entity.introduced_commit
        lines.append(f"Introduced in commit {c.sha}: {c.message}")
        lines.append(f"Commit URL: {c.url}")
    for pr in prs:
        lines.append(f"Discussed in PR #{pr.number}: {pr.title}")
        lines.append(f"PR URL: {pr.url}")
        for num in pr.issue_numbers:
            issue = next((i for i in issues if i.number == num), None)
            if issue:
                lines.append(f"References issue #{issue.number}: {issue.title}")
                lines.append(f"Issue URL: {issue.url}")
    lines.append(f"Repository: https://github.com/{owner}/{repo}")
    return "\n".join(lines)


async def remember_entity(
    document: str | CodeEntity,
    dataset_name: str,
    run_in_background: bool | None = None,
) -> Any:
    """Store entity in Cognee and wait until the remote/local pipeline finishes."""
    import cognee

    # Cloud remember() must block per request — background mode returns immediately
    # and local status polling does not see remote pipeline runs.
    background = False if run_in_background is None else run_in_background
    if run_in_background is None:
        background = not is_cloud_mode()

    result = await cognee.remember(
        document,
        dataset_name=dataset_name,
        run_in_background=background,
        self_improvement=False,
    )

    if hasattr(result, "__await__"):
        result = await result

    dataset_id, status, error = parse_remember_result(result)
    if status == "errored":
        raise RuntimeError(error or "Cognee remember failed")
    if status not in ("completed", "session_stored", "unknown"):
        logger.warning("remember_unexpected_status", status=status, dataset_id=dataset_id)

    return result


async def get_dataset_status(dataset_id: str) -> str | None:
    """Poll dataset processing status (local mode only)."""
    if is_cloud_mode():
        return None

    import asyncio

    import cognee

    try:
        status_map = await asyncio.wait_for(
            cognee.datasets.get_status([dataset_id]),
            timeout=15,
        )
        return status_map.get(str(dataset_id))
    except Exception as exc:
        logger.warning("dataset_status_poll_failed", dataset_id=dataset_id, error=str(exc))
        return None


async def recall_why(
    query: str, dataset_name: str, dataset_id: str | None = None
) -> list[Any]:
    """Query with graph-traversal search for traceable answers."""
    import cognee

    try:
        from cognee.modules.search.types import SearchType
    except ImportError:
        try:
            from cognee.api.v1.search import SearchType  # type: ignore[no-redef]
        except ImportError:
            SearchType = None  # type: ignore[misc,assignment]

    kwargs: dict[str, Any] = {
        "query_text": query,
        "verbose": True,
    }
    if dataset_id:
        kwargs["dataset_ids"] = [dataset_id]
    else:
        kwargs["datasets"] = [dataset_name]
    if SearchType is not None:
        kwargs["query_type"] = SearchType.GRAPH_COMPLETION

    return await cognee.recall(**kwargs)


def normalize_recall_results(results: Any) -> list[Any]:
    """Flatten cloud/local recall payloads into a list of items."""
    if results is None:
        return []
    if isinstance(results, list):
        return results
    if isinstance(results, dict):
        if "results" in results and isinstance(results["results"], list):
            return results["results"]
        if "text" in results or "raw" in results:
            return [results]
    return [results]


async def forget_dataset(dataset_name: str) -> None:
    """Remove all memory for a repo dataset."""
    import cognee

    await cognee.forget(dataset=dataset_name)
    logger.info("cognee_dataset_forgotten", dataset=dataset_name)


def estimate_ingest_cost(file_count: int, chunk_size: int = 1500) -> dict[str, Any]:
    """Dry-run token/LLM call estimator (inspired by cognee #3643)."""
    settings = get_settings()
    avg_file_bytes = 4000
    total_bytes = file_count * avg_file_bytes
    chunk_count = max(1, total_bytes // chunk_size)
    llm_calls = chunk_count * 2 + max(1, chunk_count // 5)
    cost = round(llm_calls * settings.dry_run_cost_per_chunk, 4)
    return {
        "file_count": file_count,
        "chunk_count": chunk_count,
        "estimated_llm_calls": llm_calls,
        "estimated_cost_usd": cost,
    }
