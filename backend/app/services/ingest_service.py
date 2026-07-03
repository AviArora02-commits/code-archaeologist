"""Ingestion orchestration: clone → extract → enrich → Cognee."""

from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path
from typing import Any

import structlog
from git import Repo

from app.config import get_settings
from app.db import Database
from app.languages import LANGUAGE_LABELS
from app.models.schemas import DryRunEstimate
from app.services import cognee_service
from app.services.git_service import (
    clone_repository,
    enrich_entity_history,
    extract_entities_from_file,
    parse_github_url,
    walk_code_files,
)
from app.services.github_service import GitHubService
from app.services.graph_service import GraphService
from app.services.language_scan import scan_unsupported_extensions

logger = structlog.get_logger()


class IngestService:
    """Coordinates repo intake and Cognee ingestion."""

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()
        self.settings = get_settings()
        self.graph = GraphService(self.db)

    async def dry_run(
        self, url: str, subfolder: str | None = None, github_token: str | None = None
    ) -> tuple[dict[str, Any], DryRunEstimate]:
        """Clone, walk files, and estimate ingestion cost without Cognee calls."""
        parsed = parse_github_url(url)
        clone_path = Path(self.settings.clone_dir) / f"{parsed.owner}_{parsed.name}_dryrun"
        await asyncio.to_thread(clone_repository, url, clone_path)
        files = await asyncio.to_thread(walk_code_files, clone_path, subfolder)
        languages = Counter(f.language for f in files)
        unsupported = await asyncio.to_thread(scan_unsupported_extensions, clone_path, subfolder)
        estimate = cognee_service.estimate_ingest_cost(len(files))
        warnings: list[str] = []
        if len(files) >= self.settings.max_files:
            warnings.append(f"File count capped at {self.settings.max_files}")
        if not files:
            warnings.append(
                f"No supported source files found. We cover {len(LANGUAGE_LABELS)}+ legacy/modern languages — "
                "request a missing one from the app."
            )
        elif unsupported:
            ext_summary = ", ".join(f"{e} ({n})" for e, n in list(unsupported.items())[:5])
            warnings.append(f"Unsupported extensions in repo: {ext_summary}")
        dry = DryRunEstimate(
            file_count=len(files),
            chunk_count=estimate["chunk_count"],
            estimated_llm_calls=estimate["estimated_llm_calls"],
            estimated_cost_usd=estimate["estimated_cost_usd"],
            skipped_files=0,
            languages=dict(languages),
            unsupported_extensions=unsupported,
            supported_language_count=len(LANGUAGE_LABELS),
            warnings=warnings,
        )
        repo_row = await self.db.create_repo(
            owner=parsed.owner,
            name=parsed.name,
            url=parsed.url,
            dataset_name=f"{parsed.owner}_{parsed.name}",
            subfolder=subfolder,
        )
        job = await self.db.create_job(repo_row["id"], dry_run_estimate=dry.model_dump())
        return {"repo": repo_row, "job": job, "clone_path": str(clone_path)}, dry

    async def run_ingestion(self, job_id: str, github_token: str | None = None) -> None:
        """Execute full ingestion pipeline for a confirmed job."""
        try:
            await self._run_ingestion(job_id, github_token)
        except Exception as exc:
            logger.exception("ingestion_failed", job_id=job_id)
            await self.db.update_job(
                job_id,
                status="failed",
                error_message=str(exc)[:500],
                progress_message="Ingestion failed",
            )

    async def _run_ingestion(self, job_id: str, github_token: str | None = None) -> None:
        """Execute full ingestion pipeline for a confirmed job."""
        job = await self.db.get_job(job_id)
        if not job:
            raise ValueError("Job not found")
        repo = await self.db.get_repo(job["repo_id"])
        if not repo:
            raise ValueError("Repo not found")

        await self.db.update_job(job_id, status="running", progress_message="Initializing Cognee")
        await cognee_service.init_cognee()

        clone_path = Path(self.settings.clone_dir) / f"{repo['owner']}_{repo['name']}"
        if not clone_path.exists():
            await self.db.update_job(job_id, progress_message="Cloning repository")
            await asyncio.to_thread(clone_repository, repo["url"], clone_path)

        await self.db.update_repo(repo["id"], clone_path=str(clone_path))
        files = await asyncio.to_thread(walk_code_files, clone_path, repo.get("subfolder"))
        if not files:
            await self.db.update_job(
                job_id,
                status="failed",
                error_message=(
                    "No supported code files found. We index 70+ legacy and modern languages "
                    "(COBOL, Fortran, RPG, PL/I, JCL, VB6, Perl, Java, C/C++, Python, etc.). "
                    "Use Request a language in the app if yours is missing."
                ),
            )
            return

        await self.db.update_job(
            job_id, total_files=len(files), progress_message="Extracting code entities"
        )

        git_repo = Repo(clone_path)
        github = GitHubService(token=github_token)
        dataset_name = repo["dataset_name"]
        dataset_id: str | None = None
        pr_cache: dict[str, list] = {}
        issue_cache: dict[int, Any] = {}
        remembered = 0

        for idx, file_rec in enumerate(files):
            file_path = clone_path / file_rec.path
            entities = extract_entities_from_file(file_path, file_rec.path, file_rec.language)
            entities = await asyncio.to_thread(
                enrich_entity_history, git_repo, entities, repo["owner"], repo["name"]
            )

            file_docs: list[str] = []
            for entity in entities:
                sha = entity.introduced_commit.sha if entity.introduced_commit else None
                prs = []
                if sha:
                    if sha not in pr_cache:
                        pr_cache[sha] = await github.link_commit_to_prs(
                            repo["owner"], repo["name"], sha
                        )
                    prs = pr_cache[sha]

                issues = []
                for pr in prs:
                    for num in pr.issue_numbers:
                        if num not in issue_cache:
                            issue_cache[num] = await github.get_issue(
                                repo["owner"], repo["name"], num
                            )
                        if issue_cache[num]:
                            issues.append(issue_cache[num])

                file_docs.append(
                    cognee_service.entity_to_document(
                        entity, prs, issues, repo["owner"], repo["name"]
                    )
                )
                sha = entity.introduced_commit.sha if entity.introduced_commit else None
                await self.graph.record_entity(
                    repo["id"],
                    entity_name=entity.entity_name,
                    entity_kind=entity.kind,
                    file_path=entity.file_path,
                    language=entity.language,
                    commit_sha=sha,
                )

            # Blocking remember per file — on Cognee Cloud this waits for remote indexing.
            if file_docs:
                combined = "\n\n---\n\n".join(file_docs)
                await self.db.update_job(
                    job_id,
                    progress_message=f"Indexing file {idx + 1}/{len(files)} in Cognee",
                )
                result = await cognee_service.remember_entity(combined, dataset_name)
                remembered += 1
                dataset_id, _, _ = cognee_service.parse_remember_result(result)
                if dataset_id:
                    await self.db.update_repo(repo["id"], cognee_dataset_id=dataset_id)

            await self.db.update_job(
                job_id,
                files_processed=idx + 1,
                progress_message=f"Indexed {idx + 1}/{len(files)} files",
            )

        if remembered == 0:
            await self.db.update_job(
                job_id,
                status="failed",
                error_message="No code entities extracted from matched files.",
            )
            return

        if dataset_id:
            await self.db.update_repo(repo["id"], cognee_dataset_id=dataset_id)

        await self.db.upsert_memory_node(
            repo["id"],
            node_type="repo",
            label=f"{repo['owner']}/{repo['name']}",
            ref_key=f"repo:{repo['id']}",
            detail=repo["dataset_name"],
        )

        await self.db.update_job(job_id, status="completed", progress_message="Ingestion complete")
