"""Utility functions: content hash, file I/O, path resolution."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def content_hash(text: str) -> str:
    """Return sha256 hash of text content."""
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()[:16]}"


def path_hash(path: str) -> str:
    """Return short hash of a file path (for snapshot naming)."""
    return hashlib.sha256(path.encode()).hexdigest()[:12]


def resolve_link_target(target: str, source_file: Path, project_root: Path) -> Path | None:
    """Resolve a link target to an absolute path.

    Tries multiple strategies:
    1. Relative to source file's directory
    2. Relative to project root
    3. With .md extension appended
    """
    # Strip leading ./ if present (but preserve ../)
    if target.startswith("./"):
        target = target[2:]

    candidates = []

    # Relative to source file directory
    source_dir = source_file.parent
    candidates.append(source_dir / target)
    if not target.endswith(".md"):
        candidates.append(source_dir / f"{target}.md")

    # Relative to project root
    candidates.append(project_root / target)
    if not target.endswith(".md"):
        candidates.append(project_root / f"{target}.md")

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file():
            return resolved

    return None


def relative_path(path: Path, project_root: Path) -> str:
    """Return path relative to project root as string."""
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path)


def find_project_root(start: Path | None = None) -> Path:
    """Find the user's project root.

    Uses CLAUDE_PROJECT_DIR env var (set by Claude Code) if available,
    otherwise falls back to marker-based detection from cwd.
    """
    # Prefer CLAUDE_PROJECT_DIR set by Claude Code
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root).resolve()

    if start is None:
        start = Path.cwd()

    current = start.resolve()
    markers = [".git", ".claude", "pyproject.toml"]

    while current != current.parent:
        for marker in markers:
            if (current / marker).exists():
                return current
        current = current.parent

    return start.resolve()
