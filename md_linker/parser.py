"""Markdown link parser: wikilinks, standard links, reference links, frontmatter deps."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import frontmatter


@dataclass
class Link:
    """A parsed link from a markdown file."""

    target: str  # file path (without section)
    section: str | None  # section anchor (None = document-level)
    link_type: str  # "wikilink", "markdown", "reference", "frontmatter"
    line: int  # 1-based line number


@dataclass
class ParseResult:
    """Result of parsing a single markdown file."""

    headings: list[str] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    frontmatter_deps: list[str] = field(default_factory=list)
    content_hash: str = ""


# Patterns
_WIKILINK_RE = re.compile(
    r"\[\["
    r"([^\]|#]+)"  # target path
    r"(?:#([^\]|]+))?"  # optional #section
    r"(?:\|[^\]]+)?"  # optional |alias
    r"\]\]"
)

_MARKDOWN_LINK_RE = re.compile(
    r"\[(?:[^\]]*)\]"  # [text]
    r"\("
    r"([^)#\s]+)"  # target path
    r"(?:#([^)\s]*))?"  # optional #section
    r"\)"
)

_REFERENCE_DEF_RE = re.compile(
    r"^\[([^\]]+)\]:\s+"  # [ref]:
    r"(\S+)"  # target URL/path
    r"(?:\s|$)",
    re.MULTILINE,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#*)?$", re.MULTILINE)


def _is_md_path(target: str) -> bool:
    """Check if target looks like a markdown file reference (not a URL)."""
    if target.startswith(("http://", "https://", "mailto:", "ftp://")):
        return False
    if target.startswith("#"):
        return False
    return True


def parse_file(file_path: Path) -> ParseResult:
    """Parse a markdown file and extract links, headings, and frontmatter deps."""
    from .utils import content_hash as compute_hash

    text = file_path.read_text(encoding="utf-8")
    result = ParseResult(content_hash=compute_hash(text))

    # Parse frontmatter
    metadata, content = frontmatter.loads(text)
    deps = metadata.get("depends-on", [])
    if isinstance(deps, list):
        result.frontmatter_deps = [str(d) for d in deps]

    # Extract headings
    for match in _HEADING_RE.finditer(content):
        result.headings.append(match.group(2).strip())

    # We need line numbers relative to the full file (including frontmatter)
    lines = text.split("\n")

    # Track which character offsets belong to which line
    line_offsets: list[tuple[int, int]] = []
    offset = 0
    for line_text in lines:
        line_offsets.append((offset, offset + len(line_text)))
        offset += len(line_text) + 1  # +1 for newline

    def _offset_to_line(pos: int) -> int:
        """Convert character offset to 1-based line number."""
        for i, (start, end) in enumerate(line_offsets):
            if start <= pos <= end:
                return i + 1
        return 1

    # Extract wikilinks
    for match in _WIKILINK_RE.finditer(text):
        target = match.group(1).strip()
        section = match.group(2)
        if section:
            section = section.strip()
        result.links.append(
            Link(
                target=target,
                section=section,
                link_type="wikilink",
                line=_offset_to_line(match.start()),
            )
        )

    # Extract markdown links
    for match in _MARKDOWN_LINK_RE.finditer(text):
        target = match.group(1).strip()
        if not _is_md_path(target):
            continue
        section = match.group(2)
        if section:
            section = section.strip()
        result.links.append(
            Link(
                target=target,
                section=section if section else None,
                link_type="markdown",
                line=_offset_to_line(match.start()),
            )
        )

    # Extract reference-style link definitions
    for match in _REFERENCE_DEF_RE.finditer(text):
        target = match.group(2).strip()
        if not _is_md_path(target):
            continue
        result.links.append(
            Link(
                target=target,
                section=None,
                link_type="reference",
                line=_offset_to_line(match.start()),
            )
        )

    return result


def extract_sections(text: str) -> dict[str, str]:
    """Extract heading-delimited sections from markdown text.

    Returns dict of {heading_text: section_content} where section_content
    is everything from the heading line to the next heading of same or higher level.
    """
    lines = text.split("\n")
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_level: int = 0
    current_lines: list[str] = []

    for line in lines:
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            # Save previous section
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines)

            current_heading = heading_match.group(2).strip()
            current_level = len(heading_match.group(1))
            current_lines = [line]
        elif current_heading is not None:
            current_lines.append(line)

    # Save last section
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines)

    return sections
