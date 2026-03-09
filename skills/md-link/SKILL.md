---
name: md-link
description: "Manage markdown cross-references and detect stale links. Auto-triggers when markdown documents have broken or semantically stale links. Tracks [[wikilinks]], standard markdown links, and frontmatter depends-on declarations."
user-invocable: true
argument-hint: "[init|status|graph|rebuild|resolve]"
allowed-tools: Read, Bash, Glob, Grep
---

# md-link: Markdown Link Management

You are managing markdown cross-references for this project using the `md-linker` tool.

## Available Commands

Run these via `uv run --project "${CLAUDE_SKILL_DIR}/.." python -m md_linker.cli <command>`:

- **init** — Scan all `.md` files and build the link graph (`.md-linker/graph.json`). Run this first in a new project.
- **status** — Show all stale documents with their summaries.
- **graph** — Output a mermaid dependency graph of all markdown links.
- **rebuild** — Rebuild the link graph from scratch (clears snapshots/diffs).
- **resolve** — Remove all `stale-refs` frontmatter annotations from all files.

## When to Use

Based on the user's argument (`$ARGUMENTS`), run the corresponding command:

```bash
uv run --project "${CLAUDE_SKILL_DIR}/.." python -m md_linker.cli $ARGUMENTS
```

If no argument is given, run `status` to show the current state.

## Understanding Stale References

When you read a markdown file that has `stale-refs` in its frontmatter, it means:
- Another document that this file links to has been modified
- The `summary` field describes what changed
- You should update the relevant sections of this file to reflect those changes
- After updating, the post-hook will automatically remove the stale annotation

Example frontmatter:
```yaml
---
stale-refs:
  - source: docs/schema.md
    changed_at: 2026-03-09T10:30:00
    sections_changed: ["User Model"]
    summary: "User 모델에 email_verified 필드 추가, role enum에 admin 값 추가됨"
---
```

## Link Syntax

The tool tracks these link types:
- `[[target]]` — wikilink (document-level)
- `[[target#Section]]` — wikilink (section-level)
- `[text](path.md)` — standard markdown link
- `[ref]: path.md` — reference-style link
- `depends-on` frontmatter field
