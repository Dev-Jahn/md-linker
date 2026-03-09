# md-linker

Markdown link graph and staleness detection plugin for Claude Code.

## Why I made this

In agentic coding workflows, Claude Code generates and maintains many markdown documents — analysis reports, plans, progress logs, specs. But sessions end, context windows are finite, and documents drift out of sync. When the agent reads an outdated document in a later session, it reasons from stale information, leading to hallucination and inconsistent decisions.

md-linker turns your project's markdown files into a lightweight internal RAG system. It tracks cross-references between documents, detects when a linked document has changed, and ensures the agent always reads up-to-date content — eliminating a major source of context-related errors across sessions.

## What it does

When you edit a markdown file, md-linker automatically:

1. **Detects broken links** — warns immediately if any `[[wikilinks]]` or `[markdown](links.md)` point to missing targets
2. **Marks stale documents** — finds all documents that reference the changed file and adds `stale-refs` annotations to their frontmatter
3. **Summarizes changes** — generates a concise diff summary (via Sonnet sub-agent) so Claude knows what changed without reading the full document

When Claude reads a stale document, a PreToolUse hook resolves the `stale-refs` via a Sonnet sub-agent before the main agent sees the file — keeping the main context clean.

## Installation

```bash
claude plugin install md-linker
```

Or for local development:

```bash
claude --plugin-dir /path/to/md-linker
```

## Usage

### Automatic (via hooks)

Once installed, md-linker works automatically. Every time Claude edits a `.md` file:

- **SessionStart** — detects external file changes (user edits, deletions, moves) by comparing content hashes, marks affected documents stale, and re-indexes the graph
- **PreToolUse (Write|Edit)** — snapshots the file before modification
- **PreToolUse (Read)** — resolves `stale-refs` via Sonnet sub-agent before the main agent reads the file
- **PostToolUse (Write|Edit) sync** — diffs, updates the link graph, detects broken links, and marks stale documents
- **PostToolUse (Write|Edit) async** — generates change summaries in the background

### Manual (via commands)

```
/md-linker:init       # Scan all .md files and build the link graph
/md-linker:status     # Show all stale documents
/md-linker:graph      # Generate a dependency graph (PNG or .dot)
/md-linker:rebuild    # Rebuild graph from scratch
/md-linker:resolve    # Remove all stale-refs annotations
```

## Link syntax

md-linker tracks these link types:

- `[[target]]` — wikilink (document-level)
- `[[target#Section]]` — wikilink (section-level)
- `[text](path.md)` — standard markdown link
- `[ref]: path.md` — reference-style link
- `depends-on` frontmatter field

## Stale reference format

When a linked document is modified, md-linker adds frontmatter like this:

```yaml
---
stale-refs:
  - source: docs/schema.md
    changed_at: 2026-03-09T10:30:00
    sections_changed: ["User Model"]
    summary: "Added email_verified field to User model"
---
```

## Requirements

- Python 3.10+
- Claude Code 1.0.33+
- No external Python dependencies (stdlib only)

## Contributing

This project is under active development. Bug reports, corner case discoveries, and improvement suggestions are all welcome — feel free to open an issue or pull request.

## License

MIT
