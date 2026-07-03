"""Unit tests for git parsing and file walking."""

from pathlib import Path

import pytest

from app.services.git_service import (
    extract_entities_from_file,
    parse_github_url,
    walk_code_files,
)
from app.services.github_service import GitHubService

FIXTURE_REPO = Path(__file__).parent.parent / "fixtures" / "sample_repo"


def test_parse_github_url_valid() -> None:
    parsed = parse_github_url("https://github.com/octocat/Hello-World")
    assert parsed.owner == "octocat"
    assert parsed.name == "Hello-World"


def test_parse_github_url_invalid() -> None:
    with pytest.raises(ValueError):
        parse_github_url("https://gitlab.com/foo/bar")


def test_walk_code_files_respects_language_filter() -> None:
    files = walk_code_files(FIXTURE_REPO)
    extensions = {Path(f.path).suffix for f in files}
    assert ".py" in extensions or ".ts" in extensions
    allowed = {"python", "javascript", "typescript", "gitconfig", "markdown"}
    assert all(f.language in allowed for f in files)


def test_extract_python_entities() -> None:
    entities = extract_entities_from_file(
        FIXTURE_REPO / "math_utils.py", "math_utils.py", "python"
    )
    names = {e.entity_name for e in entities}
    assert "add" in names
    assert "Calculator" in names


def test_github_issue_regex_fallback() -> None:
    gh = GitHubService()
    nums = gh.parse_issue_refs_from_text("This closes #42 and fixes #7")
    assert 42 in nums
    assert 7 in nums
