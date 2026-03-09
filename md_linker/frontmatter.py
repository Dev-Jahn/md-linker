"""Minimal frontmatter parser/serializer using only stdlib.

Handles the YAML subset needed for md-linker:
- Simple key: value pairs (strings)
- Block sequences (- item)
- Inline sequences [item1, item2]
- Block mappings with nested keys
- Lists of dicts (for stale-refs)
"""

from __future__ import annotations

import re
from pathlib import Path


def load(file_path: str | Path) -> tuple[dict, str]:
    """Load a markdown file and return (metadata, content)."""
    text = Path(file_path).read_text(encoding="utf-8")
    return loads(text)


def loads(text: str) -> tuple[dict, str]:
    """Parse frontmatter from text. Returns (metadata, content)."""
    if not text.startswith("---"):
        return {}, text

    # Find closing ---
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    yaml_text = text[4:end]  # Skip opening ---\n
    content = text[end + 4:]  # Skip \n---
    if content.startswith("\n"):
        content = content[1:]

    metadata = _parse_yaml(yaml_text)
    return metadata, content


def dumps(metadata: dict, content: str) -> str:
    """Serialize metadata and content back to frontmatter format."""
    if not metadata:
        if content.startswith("---"):
            return content
        return f"---\n---\n\n{content}"

    yaml_text = _dump_yaml(metadata)
    return f"---\n{yaml_text}---\n\n{content}"


# --- YAML Parser (minimal subset) ---


def _parse_yaml(text: str) -> dict:
    """Parse a minimal YAML subset into a dict."""
    lines = text.split("\n")
    return _parse_mapping(lines, 0, 0)[0]


def _parse_mapping(lines: list[str], start: int, indent: int) -> tuple[dict, int]:
    """Parse a YAML mapping at the given indentation level."""
    result: dict = {}
    i = start

    while i < len(lines):
        line = lines[i]

        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue

        # Check indentation
        line_indent = len(line) - len(line.lstrip())
        if line_indent < indent:
            break

        stripped = line.strip()

        # Check for key: value
        key_match = re.match(r"^(\s*)([^:\s][^:]*?):\s*(.*?)$", line)
        if not key_match:
            i += 1
            continue

        key_indent = len(key_match.group(1))
        if key_indent != indent:
            if key_indent < indent:
                break
            i += 1
            continue

        key = key_match.group(2).strip()
        value_str = key_match.group(3).strip()

        if value_str:
            # Inline value
            result[key] = _parse_scalar(value_str)
            i += 1
        else:
            # Value on next lines (block sequence or nested mapping)
            i += 1
            if i < len(lines):
                next_line = lines[i] if i < len(lines) else ""
                next_stripped = next_line.strip()
                next_indent = len(next_line) - len(next_line.lstrip()) if next_stripped else indent + 2

                if next_stripped.startswith("- "):
                    # Block sequence
                    value, i = _parse_sequence(lines, i, next_indent)
                    result[key] = value
                elif next_stripped and next_indent > indent:
                    # Nested mapping
                    value, i = _parse_mapping(lines, i, next_indent)
                    result[key] = value
                else:
                    result[key] = None
            else:
                result[key] = None

    return result, i


def _parse_sequence(lines: list[str], start: int, indent: int) -> tuple[list, int]:
    """Parse a YAML block sequence."""
    result: list = []
    i = start

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        line_indent = len(line) - len(line.lstrip())
        if line_indent < indent:
            break

        stripped = line.strip()
        if not stripped.startswith("- "):
            if line_indent <= indent:
                break
            i += 1
            continue

        # Get the content after "- "
        item_content = stripped[2:]

        # Check if this is a dict item (- key: value)
        dict_match = re.match(r"^([^:\s][^:]*?):\s*(.*?)$", item_content)
        if dict_match:
            # Start of a dict in the sequence
            item_dict: dict = {}
            first_key = dict_match.group(1).strip()
            first_value = dict_match.group(2).strip()
            item_dict[first_key] = _parse_scalar(first_value) if first_value else None

            # Look for more keys at deeper indent
            i += 1
            # The continuation keys are indented relative to the "- " marker
            cont_indent = indent + 2
            while i < len(lines):
                cont_line = lines[i]
                if not cont_line.strip():
                    i += 1
                    continue
                cont_line_indent = len(cont_line) - len(cont_line.lstrip())
                if cont_line_indent < cont_indent:
                    break
                cont_match = re.match(r"^\s*([^:\s][^:]*?):\s*(.*?)$", cont_line)
                if cont_match:
                    ck = cont_match.group(1).strip()
                    cv = cont_match.group(2).strip()
                    item_dict[ck] = _parse_scalar(cv) if cv else None
                    i += 1
                else:
                    break

            result.append(item_dict)
        else:
            # Simple scalar item
            result.append(_parse_scalar(item_content))
            i += 1

    return result, i


def _parse_scalar(value: str) -> str | list | None:
    """Parse a YAML scalar value."""
    if not value:
        return None

    # Inline list: ["item1", "item2"]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in _split_inline_list(inner):
            item = item.strip()
            item = _unquote(item)
            items.append(item)
        return items

    # Quoted string
    value = _unquote(value)
    return value


def _unquote(s: str) -> str:
    """Remove surrounding quotes from a string."""
    if len(s) >= 2:
        if (s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'"):
            return s[1:-1]
    return s


def _split_inline_list(text: str) -> list[str]:
    """Split an inline YAML list, respecting quotes."""
    items = []
    current = ""
    in_quotes = False
    quote_char = ""

    for ch in text:
        if ch in ('"', "'") and not in_quotes:
            in_quotes = True
            quote_char = ch
            current += ch
        elif ch == quote_char and in_quotes:
            in_quotes = False
            current += ch
        elif ch == "," and not in_quotes:
            items.append(current.strip())
            current = ""
        else:
            current += ch

    if current.strip():
        items.append(current.strip())

    return items


# --- YAML Serializer (minimal subset) ---


def _dump_yaml(data: dict, indent: int = 0) -> str:
    """Serialize a dict to minimal YAML."""
    lines: list[str] = []
    prefix = "  " * indent

    for key, value in data.items():
        if value is None:
            lines.append(f"{prefix}{key}:")
        elif isinstance(value, str):
            lines.append(f"{prefix}{key}: {_quote_if_needed(value)}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            elif all(isinstance(item, str) for item in value):
                # Simple string list
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {_quote_if_needed(item)}")
            elif all(isinstance(item, dict) for item in value):
                # List of dicts
                lines.append(f"{prefix}{key}:")
                for item in value:
                    first = True
                    for k, v in item.items():
                        if first:
                            lines.append(f"{prefix}  - {k}: {_format_value(v)}")
                            first = False
                        else:
                            lines.append(f"{prefix}    {k}: {_format_value(v)}")
            else:
                # Mixed list — use inline format
                formatted = ", ".join(_format_value(item) for item in value)
                lines.append(f"{prefix}{key}: [{formatted}]")
        elif isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dump_yaml(value, indent + 1))
        else:
            lines.append(f"{prefix}{key}: {value}")

    result = "\n".join(lines)
    if not result.endswith("\n"):
        result += "\n"
    return result


def _format_value(value: object) -> str:
    """Format a value for inline YAML output."""
    if value is None:
        return ""
    if isinstance(value, str):
        return _quote_if_needed(value)
    if isinstance(value, list):
        items = ", ".join(_quote_if_needed(str(i)) for i in value)
        return f"[{items}]"
    return str(value)


def _quote_if_needed(s: str) -> str:
    """Quote a string if it contains special YAML characters."""
    if not s:
        return '""'
    # Quote if contains characters that could be misinterpreted
    needs_quote = any(c in s for c in ":{[]},#&*!|>'\"%@`")
    # Also quote if it looks like a number, boolean, or null
    if s.lower() in ("true", "false", "null", "yes", "no", "on", "off"):
        needs_quote = True
    if needs_quote:
        escaped = s.replace('"', '\\"')
        return f'"{escaped}"'
    return s
