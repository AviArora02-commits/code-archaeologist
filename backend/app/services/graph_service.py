"""Build knowledge graph views from stored memory nodes."""

from __future__ import annotations

from app.db import Database
from app.models.schemas import GraphEdge, GraphNode, KnowledgeGraphResponse


class GraphService:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    async def get_repo_graph(self, repo_id: str) -> KnowledgeGraphResponse:
        repo = await self.db.get_repo(repo_id)
        if not repo:
            raise ValueError("Repository not found")

        nodes_raw = await self.db.list_memory_nodes(repo_id)
        edges_raw = await self.db.list_memory_edges(repo_id)

        nodes = [
            GraphNode(
                id=n["id"],
                label=n["label"],
                kind=n["node_type"],
                detail=n.get("detail"),
            )
            for n in nodes_raw
        ]
        edges = [
            GraphEdge(
                id=e["id"],
                source=e["source_id"],
                target=e["target_id"],
                kind=e["edge_type"],
            )
            for e in edges_raw
        ]

        by_kind: dict[str, int] = {}
        for n in nodes:
            by_kind[n.kind] = by_kind.get(n.kind, 0) + 1

        return KnowledgeGraphResponse(
            repo_id=repo_id,
            dataset_name=repo["dataset_name"],
            cognee_dataset_id=repo.get("cognee_dataset_id"),
            nodes=nodes,
            edges=edges,
            stats={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "by_kind": by_kind,
                "persisted_in_cognee": bool(repo.get("cognee_dataset_id")),
            },
        )

    async def record_entity(
        self,
        repo_id: str,
        *,
        entity_name: str,
        entity_kind: str,
        file_path: str,
        language: str,
        commit_sha: str | None = None,
    ) -> None:
        entity_id = await self.db.upsert_memory_node(
            repo_id,
            node_type="entity",
            label=entity_name,
            ref_key=f"entity:{file_path}:{entity_name}",
            detail=f"{entity_kind} · {language}",
        )
        file_id = await self.db.upsert_memory_node(
            repo_id,
            node_type="file",
            label=file_path.split("/")[-1] or file_path,
            ref_key=f"file:{file_path}",
            detail=file_path,
        )
        await self.db.upsert_memory_edge(repo_id, entity_id, file_id, "defined_in")

        if commit_sha:
            commit_id = await self.db.upsert_memory_node(
                repo_id,
                node_type="commit",
                label=commit_sha[:7],
                ref_key=f"commit:{commit_sha}",
                detail=commit_sha,
            )
            await self.db.upsert_memory_edge(repo_id, entity_id, commit_id, "introduced_in")
