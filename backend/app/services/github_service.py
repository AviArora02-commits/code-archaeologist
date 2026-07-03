"""GitHub REST/GraphQL enrichment with rate-limit handling."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()

CLOSING_RE = re.compile(r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE)


@dataclass
class RateLimitState:
    remaining: int = 60
    reset_at: int = 0
    authenticated: bool = False


@dataclass
class PullRequestRecord:
    number: int
    title: str
    body: str
    state: str
    url: str
    merged_at: str | None = None
    commit_shas: list[str] = field(default_factory=list)
    issue_numbers: list[int] = field(default_factory=list)


@dataclass
class IssueRecord:
    number: int
    title: str
    body: str
    state: str
    url: str


class GitHubService:
    """GitHub API client with explicit rate-limit backoff."""

    def __init__(self, token: str | None = None) -> None:
        settings = get_settings()
        self.token = token or settings.github_token or None
        self.base_url = settings.github_api_base
        self.rate_limit = RateLimitState(remaining=5000 if self.token else 60)
        self._lock = asyncio.Lock()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self._lock:
            if self.rate_limit.remaining <= 0:
                wait = max(self.rate_limit.reset_at - int(asyncio.get_event_loop().time()), 1)
                logger.warning("github_rate_limit_wait", seconds=wait)
                await asyncio.sleep(min(wait, 60))

        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=self._headers(), **kwargs)

        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        if remaining is not None:
            self.rate_limit.remaining = int(remaining)
        if reset is not None:
            self.rate_limit.reset_at = int(reset)

        if response.status_code == 403 and "rate limit" in response.text.lower():
            retry_after = int(response.headers.get("Retry-After", "60"))
            logger.error("github_rate_limited", retry_after=retry_after)
            raise RuntimeError(
                f"GitHub rate limit exceeded. Retry after {retry_after}s. "
                "Provide a PAT for 5000 req/hr."
            )

        if response.status_code >= 400:
            raise RuntimeError(f"GitHub API error {response.status_code}: {response.text[:200]}")

        if response.status_code == 204:
            return None
        return response.json()

    async def get_commit_pulls(self, owner: str, repo: str, sha: str) -> list[dict[str, Any]]:
        """Link commit to PRs via GET /repos/{owner}/{repo}/commits/{sha}/pulls."""
        headers = self._headers()
        headers["Accept"] = "application/vnd.github+json"
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}/pulls"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
        if response.status_code == 422:
            return []
        if response.status_code >= 400:
            logger.warning("commit_pulls_failed", sha=sha, status=response.status_code)
            return []
        data = response.json()
        return data if isinstance(data, list) else []

    async def get_pr_closing_issues_graphql(
        self, owner: str, repo: str, pr_number: int
    ) -> list[int]:
        """Resolve PR → issues via GraphQL closingIssuesReferences."""
        if not self.token:
            return []
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $number) {
              closingIssuesReferences(first: 20) {
                nodes { number }
              }
            }
          }
        }
        """
        payload = {"query": query, "variables": {"owner": owner, "repo": repo, "number": pr_number}}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.github.com/graphql",
                headers=self._headers(),
                json=payload,
            )
        if response.status_code >= 400:
            return []
        data = response.json()
        try:
            nodes = (
                data["data"]["repository"]["pullRequest"]["closingIssuesReferences"]["nodes"]
            )
            return [n["number"] for n in nodes if n]
        except (KeyError, TypeError):
            return []

    def parse_issue_refs_from_text(self, text: str) -> list[int]:
        """Fallback: regex on closes|fixes|resolves #N."""
        return list({int(m) for m in CLOSING_RE.findall(text or "")})

    async def enrich_pull_request(
        self, owner: str, repo: str, pr_data: dict[str, Any]
    ) -> PullRequestRecord:
        number = int(pr_data["number"])
        title = pr_data.get("title", "")
        body = pr_data.get("body") or ""
        issue_numbers = await self.get_pr_closing_issues_graphql(owner, repo, number)
        if not issue_numbers:
            issue_numbers = self.parse_issue_refs_from_text(f"{title}\n{body}")
        return PullRequestRecord(
            number=number,
            title=title,
            body=body,
            state=pr_data.get("state", "unknown"),
            url=pr_data.get("html_url", f"https://github.com/{owner}/{repo}/pull/{number}"),
            merged_at=pr_data.get("merged_at"),
            issue_numbers=issue_numbers,
        )

    async def get_issue(self, owner: str, repo: str, number: int) -> IssueRecord | None:
        try:
            data = await self._request("GET", f"/repos/{owner}/{repo}/issues/{number}")
        except RuntimeError:
            return None
        if data.get("pull_request"):
            return None
        return IssueRecord(
            number=number,
            title=data.get("title", ""),
            body=data.get("body") or "",
            state=data.get("state", "unknown"),
            url=data.get("html_url", f"https://github.com/{owner}/{repo}/issues/{number}"),
        )

    async def link_commit_to_prs(
        self, owner: str, repo: str, sha: str
    ) -> list[PullRequestRecord]:
        pulls = await self.get_commit_pulls(owner, repo, sha)
        results: list[PullRequestRecord] = []
        for pr in pulls:
            results.append(await self.enrich_pull_request(owner, repo, pr))
        return results

    def rate_limit_status(self) -> dict[str, Any]:
        return {
            "remaining": self.rate_limit.remaining,
            "reset_at": self.rate_limit.reset_at,
            "authenticated": bool(self.token),
        }
