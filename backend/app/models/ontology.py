"""Custom Cognee DataPoint ontology for code archaeology."""

from __future__ import annotations

try:
    from cognee.infrastructure.engine import DataPoint
except ImportError:
    try:
        from cognee.modules.engine.models import DataPoint  # type: ignore[no-redef]
    except ImportError:
        from pydantic import BaseModel as DataPoint  # type: ignore[misc,assignment]


class Author(DataPoint):
    """Git commit author."""

    name: str
    email: str
    github_login: str | None = None
    metadata: dict = {"index_fields": ["name", "github_login"]}


class Commit(DataPoint):
    """Git commit node."""

    sha: str
    message: str
    timestamp: str
    url: str
    author: Author | None = None
    metadata: dict = {"index_fields": ["message", "sha"]}


class Issue(DataPoint):
    """GitHub issue."""

    number: int
    title: str
    body: str
    state: str
    url: str
    metadata: dict = {"index_fields": ["title", "body"]}


class PullRequest(DataPoint):
    """GitHub pull request."""

    number: int
    title: str
    body: str
    state: str
    url: str
    merged_at: str | None = None
    references: list[Issue] = []
    metadata: dict = {"index_fields": ["title", "body"]}


class CodeEntity(DataPoint):
    """Function, class, or file-level code entity."""

    name: str
    kind: str
    file_path: str
    language: str
    signature: str | None = None
    source_snippet: str | None = None
    introduced_in: Commit | None = None
    discussed_in: list[PullRequest] = []
    metadata: dict = {"index_fields": ["name", "signature", "source_snippet", "file_path"]}
