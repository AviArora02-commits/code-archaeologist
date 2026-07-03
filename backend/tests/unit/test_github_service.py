"""Unit tests for PR/issue linking helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.github_service import GitHubService


@pytest.mark.asyncio
async def test_link_commit_to_prs_uses_rest_endpoint() -> None:
    gh = GitHubService(token="test-token")
    fake_pr = {
        "number": 10,
        "title": "Add feature",
        "body": "Closes #5",
        "state": "closed",
        "html_url": "https://github.com/o/r/pull/10",
        "merged_at": "2024-01-01T00:00:00Z",
    }
    with patch.object(gh, "get_commit_pulls", new=AsyncMock(return_value=[fake_pr])):
        with patch.object(gh, "get_pr_closing_issues_graphql", new=AsyncMock(return_value=[])):
            prs = await gh.link_commit_to_prs("owner", "repo", "abc123")
    assert len(prs) == 1
    assert prs[0].number == 10
    assert 5 in prs[0].issue_numbers


@pytest.mark.asyncio
async def test_graphql_issue_refs() -> None:
    gh = GitHubService(token="test-token")
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "data": {
                "repository": {
                    "pullRequest": {"closingIssuesReferences": {"nodes": [{"number": 99}]}}
                }
            }
        }
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        nums = await gh.get_pr_closing_issues_graphql("o", "r", 1)
    assert nums == [99]
