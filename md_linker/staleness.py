"""Staleness: frontmatter stale-refs annotation insertion/removal."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import frontmatter


def mark_stale(
    file_path: Path,
    source: str,
    sections_changed: list[str],
    summary: str | None = None,
) -> None:
    """Add a stale-refs entry to a file's frontmatter.

    If an entry for the same source already exists, it is updated.
    """
    metadata, content = frontmatter.load(file_path)

    stale_refs: list[dict] = metadata.get("stale-refs", [])
    if not isinstance(stale_refs, list):
        stale_refs = []

    # Update existing entry or create new one
    entry = None
    for ref in stale_refs:
        if ref.get("source") == source:
            entry = ref
            break

    if entry is None:
        entry = {"source": source}
        stale_refs.append(entry)

    entry["changed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    entry["sections_changed"] = sections_changed
    if summary is not None:
        entry["summary"] = summary

    metadata["stale-refs"] = stale_refs
    file_path.write_text(frontmatter.dumps(metadata, content), encoding="utf-8")


def add_summary(file_path: Path, source: str, summary: str) -> bool:
    """Add a summary to an existing stale-refs entry.

    Returns True if the entry was found and updated, False otherwise.
    """
    metadata, content = frontmatter.load(file_path)

    stale_refs: list[dict] = metadata.get("stale-refs", [])
    if not isinstance(stale_refs, list):
        return False

    for ref in stale_refs:
        if ref.get("source") == source:
            ref["summary"] = summary
            metadata["stale-refs"] = stale_refs
            file_path.write_text(frontmatter.dumps(metadata, content), encoding="utf-8")
            return True

    return False


def remove_stale_entry(file_path: Path, source: str) -> bool:
    """Remove a specific stale-refs entry by source.

    Returns True if an entry was removed.
    Removes the stale-refs key entirely if the list becomes empty.
    """
    metadata, content = frontmatter.load(file_path)

    stale_refs: list[dict] = metadata.get("stale-refs", [])
    if not isinstance(stale_refs, list):
        return False

    original_len = len(stale_refs)
    stale_refs = [r for r in stale_refs if r.get("source") != source]

    if len(stale_refs) == original_len:
        return False

    if stale_refs:
        metadata["stale-refs"] = stale_refs
    else:
        metadata.pop("stale-refs", None)

    file_path.write_text(frontmatter.dumps(metadata, content), encoding="utf-8")
    return True


def clear_all_stale(file_path: Path) -> bool:
    """Remove all stale-refs from a file's frontmatter.

    Returns True if any entries were removed.
    """
    metadata, content = frontmatter.load(file_path)

    if "stale-refs" not in metadata:
        return False

    del metadata["stale-refs"]
    file_path.write_text(frontmatter.dumps(metadata, content), encoding="utf-8")
    return True


def get_stale_refs(file_path: Path) -> list[dict]:
    """Read stale-refs from a file's frontmatter."""
    metadata, _ = frontmatter.load(file_path)
    refs = metadata.get("stale-refs", [])
    if isinstance(refs, list):
        return refs
    return []


def get_all_stale_files(project_root: Path) -> dict[str, list[dict]]:
    """Scan all markdown files and return those with stale-refs.

    Returns {relative_path: [stale_ref_entries]}.
    """
    result: dict[str, list[dict]] = {}
    for md_file in sorted(project_root.glob("**/*.md")):
        parts = md_file.relative_to(project_root).parts
        if any(p.startswith(".") for p in parts):
            continue
        refs = get_stale_refs(md_file)
        if refs:
            rel = str(md_file.relative_to(project_root))
            result[rel] = refs
    return result
