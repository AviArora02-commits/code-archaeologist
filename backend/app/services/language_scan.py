"""Scan repos for unsupported file extensions."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.languages import LANGUAGE_EXTENSIONS, UNSUPPORTED_HINT_EXTENSIONS, detect_language
from app.services.git_service import _load_gitignore, _should_skip


def scan_unsupported_extensions(repo_root: Path, subfolder: str | None = None) -> dict[str, int]:
    """Count file extensions present in repo but not in our language map."""
    root = repo_root / subfolder if subfolder else repo_root
    if not root.exists():
        return {}
    spec = _load_gitignore(repo_root)
    unsupported: Counter[str] = Counter()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if _should_skip(path, rel, spec):
            continue
        ext = path.suffix.lower()
        if detect_language(path):
            continue
        if not ext or ext in LANGUAGE_EXTENSIONS:
            continue
        if ext in UNSUPPORTED_HINT_EXTENSIONS:
            continue
        unsupported[ext] += 1
    return dict(unsupported.most_common(20))
