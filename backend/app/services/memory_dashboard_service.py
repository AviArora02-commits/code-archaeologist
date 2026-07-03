"""Multi-repo Cognee memory overview."""

from __future__ import annotations

from app.config import get_settings
from app.db import Database
from app.models.schemas import MemoryDashboardResponse, RepoMemoryCard


class MemoryDashboardService:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    async def get_dashboard(self) -> MemoryDashboardResponse:
        settings = get_settings()
        repos = await self.db.list_repos()
        cards: list[RepoMemoryCard] = []
        total_nodes = 0
        total_expert = 0

        for repo in repos:
            job = await self.db.get_latest_job(repo["id"])
            node_count = await self.db.count_memory_nodes(repo["id"])
            expert_count = await self.db.count_expert_knowledge(repo["id"])
            total_nodes += node_count
            total_expert += expert_count
            cards.append(
                RepoMemoryCard(
                    id=repo["id"],
                    owner=repo["owner"],
                    name=repo["name"],
                    url=repo["url"],
                    dataset_name=repo["dataset_name"],
                    cognee_dataset_id=repo.get("cognee_dataset_id"),
                    job_status=job["status"] if job else None,
                    files_indexed=job.get("files_processed", 0) if job else 0,
                    total_files=job.get("total_files", 0) if job else 0,
                    memory_nodes=node_count,
                    expert_entries=expert_count,
                    cognee_persisted=bool(repo.get("cognee_dataset_id")),
                )
            )

        return MemoryDashboardResponse(
            repo_count=len(cards),
            total_memory_nodes=total_nodes,
            total_expert_entries=total_expert,
            cognee_mode=settings.cognee_mode,
            repos=cards,
            cognee_lifecycle={
                "remember": "Ingest code + expert knowledge into per-repo datasets",
                "recall": "GRAPH_COMPLETION why-queries with evidence chains",
                "improve": "Feedback thumbs-up triggers cognee.improve()",
                "forget": "Delete memory removes dataset + local graph safely",
            },
            message=(
                "Each repo is an isolated Cognee Cloud dataset. Connect 10+ legacy repos — "
                "memory persists across sessions until you explicitly forget."
            ),
        )
