"""Link graph: build, persist, query reverse links."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from .parser import Link, parse_file
from .utils import relative_path, resolve_link_target


GRAPH_VERSION = 1


@dataclass
class FileEntry:
    """A single file's entry in the link graph."""

    content_hash: str = ""
    headings: list[str] = field(default_factory=list)
    outgoing: list[dict] = field(default_factory=list)
    frontmatter_deps: list[str] = field(default_factory=list)
    last_indexed: str = ""


@dataclass
class LinkGraph:
    """The full link graph for a project."""

    version: int = GRAPH_VERSION
    files: dict[str, FileEntry] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        """Persist graph to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": self.version,
            "files": {k: asdict(v) for k, v in self.files.items()},
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> LinkGraph:
        """Load graph from JSON file. Returns empty graph if file doesn't exist."""
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            graph = cls(version=data.get("version", GRAPH_VERSION))
            for rel_path, entry_data in data.get("files", {}).items():
                graph.files[rel_path] = FileEntry(**entry_data)
            return graph
        except (json.JSONDecodeError, TypeError, KeyError):
            return cls()

    def index_file(self, file_path: Path, project_root: Path) -> FileEntry:
        """Parse and index a single file into the graph."""
        result = parse_file(file_path)
        rel = relative_path(file_path, project_root)

        outgoing = []
        for link in result.links:
            resolved = resolve_link_target(link.target, file_path, project_root)
            if resolved:
                target_rel = relative_path(resolved, project_root)
            else:
                target_rel = link.target
            outgoing.append({
                "target": target_rel,
                "section": link.section,
                "type": link.link_type,
                "line": link.line,
            })

        # Also add frontmatter deps as outgoing links
        for dep in result.frontmatter_deps:
            resolved = resolve_link_target(dep, file_path, project_root)
            if resolved:
                target_rel = relative_path(resolved, project_root)
            else:
                target_rel = dep
            outgoing.append({
                "target": target_rel,
                "section": None,
                "type": "frontmatter",
                "line": 0,
            })

        entry = FileEntry(
            content_hash=result.content_hash,
            headings=result.headings,
            outgoing=outgoing,
            frontmatter_deps=result.frontmatter_deps,
            last_indexed=datetime.now(timezone.utc).isoformat(),
        )
        self.files[rel] = entry
        return entry

    def remove_file(self, rel_path: str) -> None:
        """Remove a file from the graph."""
        self.files.pop(rel_path, None)

    def get_reverse_links(self, rel_path: str) -> list[dict]:
        """Get all files that link TO the given file.

        Returns list of {file, link_type, link_section} dicts.
        link_section is the section specified in the link (None = document-level).
        """
        reverse: list[dict] = []
        for source_path, entry in self.files.items():
            if source_path == rel_path:
                continue
            for link in entry.outgoing:
                if link["target"] == rel_path:
                    reverse.append({
                        "file": source_path,
                        "link_type": link["type"],
                        "link_section": link["section"],
                    })
        return reverse

    def get_broken_links(self, project_root: Path) -> list[dict]:
        """Find all links pointing to non-existent files or sections.

        Returns list of {source, target, section, line, type, reason} dicts.
        """
        broken: list[dict] = []
        for source_path, entry in self.files.items():
            for link in entry.outgoing:
                target = link["target"]
                target_path = project_root / target
                if not target_path.is_file():
                    broken.append({
                        "source": source_path,
                        "target": target,
                        "section": link["section"],
                        "line": link["line"],
                        "type": link["type"],
                        "reason": "file not found",
                    })
                elif link["section"] and target in self.files:
                    target_entry = self.files[target]
                    # Case-insensitive heading match
                    heading_lower = [h.lower() for h in target_entry.headings]
                    if link["section"].lower() not in heading_lower:
                        broken.append({
                            "source": source_path,
                            "target": target,
                            "section": link["section"],
                            "line": link["line"],
                            "type": link["type"],
                            "reason": "section not found",
                        })
        return broken

    def build(self, project_root: Path, glob_pattern: str = "**/*.md") -> None:
        """Scan all markdown files and build the full graph."""
        self.files.clear()
        for md_file in sorted(project_root.glob(glob_pattern)):
            # Skip hidden directories and .md-linker
            parts = md_file.relative_to(project_root).parts
            if any(p.startswith(".") for p in parts):
                continue
            self.index_file(md_file, project_root)
