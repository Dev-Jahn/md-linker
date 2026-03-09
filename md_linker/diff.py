"""Diff engine: snapshot management, diff generation, trivial change filtering."""

from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path

from .parser import _HEADING_RE
from .utils import path_hash


def get_snapshot_dir(project_root: Path) -> Path:
    """Return the snapshots directory path."""
    return project_root / ".md-linker" / "snapshots"


def get_diffs_dir(project_root: Path) -> Path:
    """Return the diffs directory path."""
    return project_root / ".md-linker" / "diffs"


def create_snapshot(file_path: Path, project_root: Path) -> Path | None:
    """Copy a file to the snapshots directory before modification.

    Returns the snapshot path, or None if file doesn't exist.
    """
    if not file_path.is_file():
        return None

    snap_dir = get_snapshot_dir(project_root)
    snap_dir.mkdir(parents=True, exist_ok=True)

    rel = str(file_path.resolve().relative_to(project_root.resolve()))
    snap_path = snap_dir / path_hash(rel)
    shutil.copy2(file_path, snap_path)
    return snap_path


def get_snapshot(file_path: Path, project_root: Path) -> Path | None:
    """Get the snapshot path for a file, if it exists."""
    rel = str(file_path.resolve().relative_to(project_root.resolve()))
    snap_path = get_snapshot_dir(project_root) / path_hash(rel)
    if snap_path.is_file():
        return snap_path
    return None


def remove_snapshot(file_path: Path, project_root: Path) -> None:
    """Remove the snapshot for a file."""
    rel = str(file_path.resolve().relative_to(project_root.resolve()))
    snap_path = get_snapshot_dir(project_root) / path_hash(rel)
    snap_path.unlink(missing_ok=True)


def generate_diff(old_text: str, new_text: str, file_path: str) -> str:
    """Generate a unified diff between old and new text."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
    )
    return "".join(diff)


def is_trivial_change(diff_text: str) -> bool:
    """Check if a diff contains only whitespace/formatting changes.

    Returns True if the diff should be skipped (no meaningful content change).
    """
    if not diff_text.strip():
        return True

    for line in diff_text.splitlines():
        if not line.startswith("+") and not line.startswith("-"):
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        # Strip the +/- prefix and check if remaining content is only whitespace
        content = line[1:]
        if content.strip():
            # There's actual content change — check if it's only whitespace restructuring
            pass
        else:
            continue

    # Compare normalized versions (collapse all whitespace)
    added_content = []
    removed_content = []
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_content.append(re.sub(r"\s+", " ", line[1:]).strip())
        elif line.startswith("-") and not line.startswith("---"):
            removed_content.append(re.sub(r"\s+", " ", line[1:]).strip())

    # Filter out empty lines
    added = [l for l in added_content if l]
    removed = [l for l in removed_content if l]

    return added == removed


def get_changed_sections(old_text: str, new_text: str) -> list[str]:
    """Determine which heading-delimited sections were changed.

    Returns list of heading texts for sections that differ between old and new.
    """
    old_sections = _split_by_headings(old_text)
    new_sections = _split_by_headings(new_text)

    changed = []
    all_headings = set(old_sections.keys()) | set(new_sections.keys())

    for heading in all_headings:
        old_content = old_sections.get(heading, "")
        new_content = new_sections.get(heading, "")
        if old_content != new_content:
            changed.append(heading)

    return changed


def _split_by_headings(text: str) -> dict[str, str]:
    """Split text into sections by headings.

    Returns {heading_text: full_section_text}.
    Content before the first heading is stored under "" key.
    """
    sections: dict[str, str] = {}
    current_heading = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if current_lines or current_heading:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines or current_heading:
        sections[current_heading] = "\n".join(current_lines)

    return sections
