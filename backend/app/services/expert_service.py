"""Expert / tribal knowledge contributed by legacy system professionals."""

from __future__ import annotations

import structlog

from app.db import Database
from app.services import cognee_service
from app.services.graph_service import GraphService

logger = structlog.get_logger()


class ExpertService:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()
        self.graph = GraphService(self.db)

    async def add_knowledge(
        self,
        repo_id: str,
        *,
        author_name: str,
        topic: str,
        content: str,
        related_file: str | None = None,
        related_symbol: str | None = None,
    ) -> dict:
        repo = await self.db.get_repo(repo_id)
        if not repo:
            raise ValueError("Repository not found")

        row = await self.db.create_expert_knowledge(
            repo_id=repo_id,
            author_name=author_name.strip(),
            topic=topic.strip(),
            content=content.strip(),
            related_file=related_file,
            related_symbol=related_symbol,
        )

        document = self._to_document(repo, row)
        await cognee_service.init_cognee()
        try:
            await cognee_service.remember_entity(document, repo["dataset_name"])
            await self.db.update_expert_knowledge(row["id"], cognee_stored=1)
            row["cognee_stored"] = 1
            try:
                import cognee

                await cognee.improve(dataset=repo["dataset_name"])
            except Exception as improve_exc:
                logger.warning("expert_improve_skipped", error=str(improve_exc))
        except Exception as exc:
            logger.warning("expert_cognee_store_failed", error=str(exc))
            await self.db.update_expert_knowledge(row["id"], cognee_stored=0)

        expert_node = await self.db.upsert_memory_node(
            repo_id,
            node_type="expert",
            label=topic[:60],
            ref_key=f"expert:{row['id']}",
            detail=f"By {author_name}",
        )
        if related_file:
            file_id = await self.db.upsert_memory_node(
                repo_id,
                node_type="file",
                label=related_file.split("/")[-1] or related_file,
                ref_key=f"file:{related_file}",
                detail=related_file,
            )
            await self.db.upsert_memory_edge(repo_id, expert_node, file_id, "explains")
        if related_symbol:
            entity_id = await self.db.upsert_memory_node(
                repo_id,
                node_type="entity",
                label=related_symbol,
                ref_key=f"entity:expert:{related_symbol}",
                detail="Expert-linked symbol",
            )
            await self.db.upsert_memory_edge(repo_id, expert_node, entity_id, "explains")

        return row

    async def list_knowledge(self, repo_id: str) -> list[dict]:
        return await self.db.list_expert_knowledge(repo_id)

    def _to_document(self, repo: dict, row: dict) -> str:
        lines = [
            "# ExpertKnowledge",
            "Type: tribal_knowledge",
            f"Author: {row['author_name']}",
            f"Topic: {row['topic']}",
            f"Repository: https://github.com/{repo['owner']}/{repo['name']}",
        ]
        if row.get("related_file"):
            lines.append(f"Related file: {row['related_file']}")
        if row.get("related_symbol"):
            lines.append(f"Related symbol: {row['related_symbol']}")
        lines.append("")
        lines.append(row["content"])
        lines.append("")
        lines.append(
            "This knowledge was contributed by an experienced professional who understands "
            "this legacy system. Prefer this over generic LLM guesses when answering why-questions."
        )
        return "\n".join(lines)
