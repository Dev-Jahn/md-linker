"""CLI entrypoint for md-linker hooks and skill commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .diff import (
    create_snapshot,
    generate_diff,
    get_changed_sections,
    get_diffs_dir,
    get_snapshot,
    is_trivial_change,
    remove_snapshot,
)
from .graph import LinkGraph
from .staleness import (
    add_summary,
    clear_all_stale,
    get_all_stale_files,
    mark_stale,
)
from .utils import find_project_root, path_hash, relative_path


def _graph_path(project_root: Path) -> Path:
    return project_root / ".md-linker" / "graph.json"


def _lock_path(project_root: Path) -> Path:
    return project_root / ".md-linker" / "updating.lock"


def _is_locked(project_root: Path) -> bool:
    return _lock_path(project_root).exists()


def _acquire_lock(project_root: Path) -> None:
    lock = _lock_path(project_root)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(str(os.getpid()))


def _release_lock(project_root: Path) -> None:
    _lock_path(project_root).unlink(missing_ok=True)


def _parse_file_path_from_stdin() -> str | None:
    """Parse file_path from hook stdin JSON."""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return None

    # Try tool_input.file_path (Edit/Write hooks)
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path")
    if file_path:
        return file_path

    return None


def _is_md_file(path: str) -> bool:
    return path.lower().endswith(".md")


# --- Hook commands ---


def cmd_pre_snapshot() -> None:
    """PreToolUse hook: create snapshot of file before modification."""
    project_root = find_project_root()

    if _is_locked(project_root):
        sys.exit(0)

    file_path = _parse_file_path_from_stdin()
    if not file_path or not _is_md_file(file_path):
        sys.exit(0)

    target = Path(file_path)
    if not target.is_absolute():
        target = project_root / target

    create_snapshot(target, project_root)
    # No stdout output (prevent context pollution)


def cmd_post_change_sync() -> None:
    """PostToolUse sync hook: diff, graph update, stale marking."""
    project_root = find_project_root()

    if _is_locked(project_root):
        sys.exit(0)

    file_path = _parse_file_path_from_stdin()
    if not file_path or not _is_md_file(file_path):
        sys.exit(0)

    target = Path(file_path)
    if not target.is_absolute():
        target = project_root / target

    rel = relative_path(target, project_root)

    # 1. Generate diff from snapshot
    snap = get_snapshot(target, project_root)
    diff_text = ""
    changed_sections: list[str] = []

    if snap and target.is_file():
        old_text = snap.read_text(encoding="utf-8")
        new_text = target.read_text(encoding="utf-8")
        diff_text = generate_diff(old_text, new_text, rel)
        changed_sections = get_changed_sections(old_text, new_text)
    elif not target.is_file():
        # File was deleted
        if snap:
            old_text = snap.read_text(encoding="utf-8")
            diff_text = generate_diff(old_text, "", rel)

    # 2. Update graph
    graph = LinkGraph.load(_graph_path(project_root))
    if target.is_file():
        graph.index_file(target, project_root)
    else:
        graph.remove_file(rel)
    graph.save(_graph_path(project_root))

    # 3. Broken link detection
    broken = graph.get_broken_links(project_root)
    if broken:
        warnings = []
        for b in broken:
            reason = b["reason"]
            warnings.append(f"  {b['source']}:{b['line']} → {b['target']}"
                          + (f"#{b['section']}" if b['section'] else "")
                          + f" ({reason})")
        print("⚠ Broken links detected:")
        for w in warnings:
            print(w)

    # 4. Trivial change filter
    if is_trivial_change(diff_text):
        remove_snapshot(target, project_root)
        sys.exit(0)

    # 5. Reverse link query + stale marking
    reverse_links = graph.get_reverse_links(rel)
    if not reverse_links:
        remove_snapshot(target, project_root)
        sys.exit(0)

    # Filter by section-level pruning
    stale_targets: list[str] = []
    for rlink in reverse_links:
        link_section = rlink["link_section"]
        if link_section is None:
            # Document-level link: always stale
            stale_targets.append(rlink["file"])
        elif link_section in changed_sections:
            # Section link: stale only if that section changed
            stale_targets.append(rlink["file"])
        # else: section link but section didn't change → skip

    # Deduplicate
    stale_targets = list(dict.fromkeys(stale_targets))

    if not stale_targets:
        remove_snapshot(target, project_root)
        sys.exit(0)

    # Mark stale (without summary — async will add it)
    try:
        _acquire_lock(project_root)
        for stale_file in stale_targets:
            stale_path = project_root / stale_file
            if stale_path.is_file():
                mark_stale(stale_path, rel, changed_sections)
    finally:
        _release_lock(project_root)

    # 6. Save diff for async processing
    diffs_dir = get_diffs_dir(project_root)
    diffs_dir.mkdir(parents=True, exist_ok=True)
    diff_info = {
        "changed_file": rel,
        "diff": diff_text,
        "changed_sections": changed_sections,
        "stale_targets": stale_targets,
    }
    diff_hash = path_hash(rel + diff_text[:200])
    diff_file = diffs_dir / f"{diff_hash}.json"
    diff_file.write_text(json.dumps(diff_info, ensure_ascii=False), encoding="utf-8")

    # 7. Cleanup snapshot
    remove_snapshot(target, project_root)

    # 8. Output stale info
    if stale_targets:
        print(f"⚠ Stale documents (due to changes in {rel}):")
        for t in stale_targets:
            print(f"  → {t}")


def cmd_post_change_async() -> None:
    """PostToolUse async hook: generate summary via sub-agent, update frontmatter."""
    project_root = find_project_root()

    diffs_dir = get_diffs_dir(project_root)
    if not diffs_dir.is_dir():
        sys.exit(0)

    diff_files = list(diffs_dir.glob("*.json"))
    if not diff_files:
        sys.exit(0)

    for diff_file in diff_files:
        try:
            data = json.loads(diff_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            diff_file.unlink(missing_ok=True)
            continue

        diff_text = data.get("diff", "")
        stale_targets = data.get("stale_targets", [])
        changed_file = data.get("changed_file", "")

        if not diff_text or not stale_targets:
            diff_file.unlink(missing_ok=True)
            continue

        # Generate summary via sub-agent (Sonnet) or deterministic fallback
        from .summarizer import summarize_diff
        summary = summarize_diff(diff_text)

        # Update frontmatter with summary
        try:
            _acquire_lock(project_root)
            for stale_file in stale_targets:
                stale_path = project_root / stale_file
                if stale_path.is_file():
                    add_summary(stale_path, changed_file, summary)
        finally:
            _release_lock(project_root)

        diff_file.unlink(missing_ok=True)


def _generate_summary_placeholder(diff_text: str) -> str:
    """Placeholder for sub-agent summary generation.

    Extracts a simple summary from the diff.
    Will be replaced with actual sub-agent call in Phase 5.
    """
    added = []
    removed = []
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            content = line[1:].strip()
            if content:
                added.append(content)
        elif line.startswith("-") and not line.startswith("---"):
            content = line[1:].strip()
            if content:
                removed.append(content)

    parts = []
    if removed:
        parts.append(f"Removed: {'; '.join(removed[:3])}")
    if added:
        parts.append(f"Added: {'; '.join(added[:3])}")

    return ". ".join(parts) if parts else "Content modified"


# --- Skill commands ---


def cmd_init() -> None:
    """Initialize: scan all .md files and build graph."""
    project_root = find_project_root()
    graph = LinkGraph()
    graph.build(project_root)
    graph.save(_graph_path(project_root))
    print(f"Initialized md-linker graph: {len(graph.files)} files indexed")

    broken = graph.get_broken_links(project_root)
    if broken:
        print(f"\n⚠ {len(broken)} broken link(s) found:")
        for b in broken:
            print(f"  {b['source']}:{b['line']} → {b['target']}"
                  + (f"#{b['section']}" if b['section'] else "")
                  + f" ({b['reason']})")


def cmd_status() -> None:
    """Show staleness report."""
    project_root = find_project_root()
    stale = get_all_stale_files(project_root)

    if not stale:
        print("No stale documents found.")
        return

    print(f"⚠ {len(stale)} stale document(s):\n")
    for file_path, refs in stale.items():
        print(f"  {file_path}:")
        for ref in refs:
            source = ref.get("source", "unknown")
            sections = ref.get("sections_changed", [])
            summary = ref.get("summary", "")
            print(f"    ← {source} (sections: {', '.join(sections)})")
            if summary:
                print(f"      {summary}")


def cmd_graph() -> None:
    """Output mermaid dependency graph."""
    project_root = find_project_root()
    graph = LinkGraph.load(_graph_path(project_root))

    if not graph.files:
        print("Graph is empty. Run `/md-link init` first.")
        return

    print("```mermaid")
    print("graph LR")

    # Create node IDs (sanitize file paths)
    node_ids: dict[str, str] = {}
    for i, path in enumerate(sorted(graph.files.keys())):
        node_id = f"n{i}"
        node_ids[path] = node_id
        label = path.replace('"', '\\"')
        print(f'  {node_id}["{label}"]')

    # Create edges
    for source_path, entry in graph.files.items():
        source_id = node_ids.get(source_path)
        if not source_id:
            continue
        seen_targets: set[str] = set()
        for link in entry.outgoing:
            target = link["target"]
            if target in seen_targets:
                continue
            seen_targets.add(target)
            target_id = node_ids.get(target)
            if target_id:
                section = link.get("section", "")
                label = f"#{section}" if section else ""
                if label:
                    print(f"  {source_id} -->|{label}| {target_id}")
                else:
                    print(f"  {source_id} --> {target_id}")

    print("```")


def cmd_rebuild() -> None:
    """Rebuild graph from scratch."""
    project_root = find_project_root()

    # Clean up .md-linker state
    md_linker_dir = project_root / ".md-linker"
    if md_linker_dir.is_dir():
        import shutil
        for subdir in ["snapshots", "diffs"]:
            d = md_linker_dir / subdir
            if d.is_dir():
                shutil.rmtree(d)

    graph = LinkGraph()
    graph.build(project_root)
    graph.save(_graph_path(project_root))
    print(f"Rebuilt md-linker graph: {len(graph.files)} files indexed")


def cmd_resolve() -> None:
    """Remove all stale-refs from all files."""
    project_root = find_project_root()
    stale = get_all_stale_files(project_root)

    if not stale:
        print("No stale documents to resolve.")
        return

    try:
        _acquire_lock(project_root)
        count = 0
        for file_path in stale:
            full_path = project_root / file_path
            if full_path.is_file():
                if clear_all_stale(full_path):
                    count += 1
    finally:
        _release_lock(project_root)

    print(f"Resolved stale-refs in {count} file(s).")


# --- Main dispatcher ---

import os  # noqa: E402 (needed for _acquire_lock)

COMMANDS = {
    "pre-snapshot": cmd_pre_snapshot,
    "post-change-sync": cmd_post_change_sync,
    "post-change-async": cmd_post_change_async,
    "init": cmd_init,
    "status": cmd_status,
    "graph": cmd_graph,
    "rebuild": cmd_rebuild,
    "resolve": cmd_resolve,
}


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: md-linker <command>")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    COMMANDS[cmd]()


if __name__ == "__main__":
    main()
