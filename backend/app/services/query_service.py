"""Why-query service: recall + evidence chain assembly."""

from __future__ import annotations

import re
from typing import Any

import structlog

from app.db import Database
from app.models.schemas import EvidenceItem, WhyQueryResponse
from app.services import cognee_service
from app.services.text_utils import extract_answer_text

logger = structlog.get_logger()

SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b")
PR_RE = re.compile(r"(?:PR|pull request)\s*#?(\d+)", re.IGNORECASE)
ISSUE_RE = re.compile(r"(?:issue)\s*#?(\d+)", re.IGNORECASE)
GITHUB_URL_RE = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/(?:commit|pull|issues)/[\w?=#]+")


class QueryService:
    """Assembles sourced evidence chains from Cognee recall results."""

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    async def ask_why(self, repo_id: str, question: str) -> WhyQueryResponse:
        repo = await self.db.get_repo(repo_id)
        if not repo:
            raise ValueError(
                "Repository not found on the server. After a deploy the registry resets — "
                "refresh the page, delete this repo from the sidebar, and connect it again."
            )

        job = await self.db.get_latest_job(repo_id)
        if not job or job.get("status") != "completed":
            raise ValueError("Ingestion not complete — wait for indexing to finish before querying.")
        if job.get("total_files", 0) == 0:
            raise ValueError("No files were indexed for this repo. Re-connect with a subfolder containing source code.")

        await cognee_service.init_cognee()
        try:
            raw_results = await cognee_service.recall_why(
                question,
                repo["dataset_name"],
                dataset_id=repo.get("cognee_dataset_id"),
            )
            results = cognee_service.normalize_recall_results(raw_results)
        except Exception as exc:
            msg = str(exc)
            if "Recall prerequisites" in msg or "404" in msg:
                raise ValueError(
                    "Memory not ready on Cognee Cloud. Delete this repo and re-ingest — "
                    "the previous ingest likely finished before data was indexed."
                ) from exc
            raise

        answer_parts: list[str] = []
        raw_sources: list[dict[str, Any]] = []
        evidence: list[EvidenceItem] = []

        for result in results:
            if isinstance(result, list):
                for item in result:
                    text = extract_answer_text(item)
                    if text:
                        answer_parts.append(text)
                    raw_sources.append(_result_to_dict(item))
                    evidence.extend(self._extract_evidence(text, repo["owner"], repo["name"]))
                continue
            text = extract_answer_text(result)
            if text:
                answer_parts.append(text)
            raw_sources.append(_result_to_dict(result))
            evidence.extend(self._extract_evidence(text, repo["owner"], repo["name"]))

        if not answer_parts:
            answer_parts.append("No results found in the knowledge graph for this query.")

        # Deduplicate evidence by label+url
        seen: set[str] = set()
        unique_evidence: list[EvidenceItem] = []
        for item in evidence:
            key = f"{item.kind}:{item.label}:{item.url}"
            if key not in seen:
                seen.add(key)
                unique_evidence.append(item)

        return WhyQueryResponse(
            answer="\n\n".join(answer_parts),
            evidence_chain=unique_evidence,
            raw_sources=raw_sources,
        )

    def _extract_evidence(self, text: str, owner: str, repo: str) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        base = f"https://github.com/{owner}/{repo}"

        for url in GITHUB_URL_RE.findall(text):
            kind: str = "text"
            if "/commit/" in url:
                kind = "commit"
            elif "/pull/" in url:
                kind = "pull_request"
            elif "/issues/" in url:
                kind = "issue"
            items.append(EvidenceItem(kind=kind, label=url, url=url))  # type: ignore[arg-type]

        for sha in SHA_RE.findall(text):
            if len(sha) >= 7:
                url = f"{base}/commit/{sha}"
                items.append(
                    EvidenceItem(kind="commit", label=f"Commit {sha[:7]}", url=url, sha=sha)
                )

        for num in PR_RE.findall(text):
            n = int(num)
            items.append(
                EvidenceItem(
                    kind="pull_request",
                    label=f"PR #{n}",
                    url=f"{base}/pull/{n}",
                    number=n,
                )
            )

        for num in ISSUE_RE.findall(text):
            n = int(num)
            items.append(
                EvidenceItem(
                    kind="issue",
                    label=f"Issue #{n}",
                    url=f"{base}/issues/{n}",
                    number=n,
                )
            )

        return items


def _result_to_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    out: dict[str, Any] = {}
    for attr in ("text", "source", "kind", "search_type", "dataset_name", "metadata", "raw"):
        if hasattr(result, attr):
            out[attr] = getattr(result, attr)
    return out
