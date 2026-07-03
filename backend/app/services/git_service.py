"""Git repository operations: clone, walk, history."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pathspec
import structlog
from git import Repo
from git.exc import GitCommandError

from app.config import get_settings
from app.languages import detect_language, get_entity_patterns

logger = structlog.get_logger()

GITHUB_URL_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<name>[\w.-]+?)(?:\.git)?/?$"
)

SKIP_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "coverage",
}

SKIP_EXTENSIONS = {
    ".lock",
    ".min.js",
    ".min.css",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
    ".class",
    ".o",
    ".a",
}


@dataclass
class ParsedRepoUrl:
    owner: str
    name: str
    url: str


@dataclass
class FileRecord:
    path: str
    language: str
    size_bytes: int


@dataclass
class CommitRecord:
    sha: str
    message: str
    author_name: str
    author_email: str
    timestamp: str
    url: str


@dataclass
class EntityHistory:
    file_path: str
    entity_name: str
    kind: str
    language: str
    signature: str | None
    source_snippet: str | None
    introduced_commit: CommitRecord | None = None
    blame_commits: list[CommitRecord] = field(default_factory=list)


def parse_github_url(url: str) -> ParsedRepoUrl:
    """Validate and parse a GitHub repository URL."""
    match = GITHUB_URL_RE.match(url.strip())
    if not match:
        raise ValueError("URL must be a valid GitHub repository URL (https://github.com/owner/repo)")
    owner = match.group("owner")
    name = match.group("name").removesuffix(".git")
    return ParsedRepoUrl(owner=owner, name=name, url=f"https://github.com/{owner}/{name}")


def clone_repository(url: str, target_dir: Path, depth: int | None = None) -> Path:
    """Shallow-clone a repository to disk using subprocess git (async-safe)."""
    import shutil
    import subprocess

    settings = get_settings()
    clone_depth = depth or settings.clone_depth
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
        if target_dir.exists():
            subprocess.run(["git", "rm", "-rf", str(target_dir)], capture_output=True)
            shutil.rmtree(target_dir, ignore_errors=True)
    logger.info("cloning_repo", url=url, depth=clone_depth, target=str(target_dir))
    try:
        subprocess.run(
            ["git", "clone", "--depth", str(clone_depth), url, str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to clone repository: {exc.stderr or exc}") from exc
    return target_dir


def _load_gitignore(repo_root: Path) -> pathspec.PathSpec | None:
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        return None
    patterns = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    from pathspec.patterns import GitWildMatchPattern

    return pathspec.PathSpec.from_lines(GitWildMatchPattern, patterns)


def _should_skip(path: Path, rel: str, spec: pathspec.PathSpec | None) -> bool:
    parts = Path(rel).parts
    if any(p in SKIP_DIRS for p in parts):
        return True
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    if path.name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "poetry.lock"}:
        return True
    if spec and spec.match_file(rel):
        return True
    return False


def walk_code_files(repo_root: Path, subfolder: str | None = None) -> list[FileRecord]:
    """Walk repository files respecting gitignore and language filters."""
    settings = get_settings()
    root = repo_root / subfolder if subfolder else repo_root
    if not root.exists():
        raise ValueError(f"Subfolder not found: {subfolder}")

    spec = _load_gitignore(repo_root)
    records: list[FileRecord] = []
    skipped = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if _should_skip(path, rel, spec):
            skipped += 1
            continue
        language = detect_language(path)
        if not language:
            continue
        size = path.stat().st_size
        if size > settings.max_file_size_kb * 1024:
            skipped += 1
            continue
        records.append(FileRecord(path=rel, language=language, size_bytes=size))
        if len(records) >= settings.max_files:
            break

    logger.info("file_walk_complete", files=len(records), skipped=skipped)
    return records


def extract_entities_from_file(file_path: Path, rel_path: str, language: str) -> list[EntityHistory]:
    """Extract function/class entities using regex heuristics."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    entities: list[EntityHistory] = []
    patterns = get_entity_patterns(language)

    for i, line in enumerate(content.splitlines(), start=1):
        for pattern, kind in patterns:
            match = re.search(pattern, line)
            if match:
                name = match.group(1)
                snippet_lines = content.splitlines()[max(0, i - 1) : i + 4]
                entities.append(
                    EntityHistory(
                        file_path=rel_path,
                        entity_name=name,
                        kind=kind,
                        language=language,
                        signature=line.strip(),
                        source_snippet="\n".join(snippet_lines),
                    )
                )
    if not entities:
        entities.append(
            EntityHistory(
                file_path=rel_path,
                entity_name=Path(rel_path).name,
                kind="file",
                language=language,
                signature=None,
                source_snippet=content[:500],
            )
        )
    return entities


def get_file_introducing_commit(repo: Repo, rel_path: str, owner: str, name: str) -> CommitRecord | None:
    """Find the earliest commit that touched a file."""
    try:
        commits = list(repo.iter_commits(paths=rel_path, max_count=1, reverse=True))
    except GitCommandError:
        return None
    if not commits:
        return None
    c = commits[0]
    return _commit_to_record(c, owner, name)


def get_blame_commits(repo: Repo, rel_path: str, owner: str, name: str) -> list[CommitRecord]:
    """Get unique commits from git blame for a file."""
    try:
        blame = repo.blame("HEAD", rel_path)
    except GitCommandError:
        return []
    seen: set[str] = set()
    records: list[CommitRecord] = []
    for commit, _lines in blame:
        if commit.hexsha in seen:
            continue
        seen.add(commit.hexsha)
        records.append(_commit_to_record(commit, owner, name))
    return records


def _commit_to_record(commit: object, owner: str, name: str) -> CommitRecord:
    c = commit  # git.Commit
    return CommitRecord(
        sha=c.hexsha,  # type: ignore[attr-defined]
        message=c.message.strip(),  # type: ignore[attr-defined]
        author_name=c.author.name if c.author else "unknown",  # type: ignore[attr-defined]
        author_email=c.author.email if c.author else "",  # type: ignore[attr-defined]
        timestamp=c.committed_datetime.isoformat(),  # type: ignore[attr-defined]
        url=f"https://github.com/{owner}/{name}/commit/{c.hexsha}",  # type: ignore[attr-defined]
    )


def enrich_entity_history(
    repo: Repo, entities: list[EntityHistory], owner: str, name: str
) -> list[EntityHistory]:
    """Attach git history to entities."""
    for entity in entities:
        entity.introduced_commit = get_file_introducing_commit(repo, entity.file_path, owner, name)
        entity.blame_commits = get_blame_commits(repo, entity.file_path, owner, name)
    return entities
