# md-linker

Markdown link graph and staleness detection plugin for Claude Code.

## What it does

When you edit a markdown file, md-linker automatically:

1. **Detects broken links** — warns immediately if any `[[wikilinks]]` or `[markdown](links.md)` point to missing targets
2. **Marks stale documents** — finds all documents that reference the changed file and adds `stale-refs` annotations to their frontmatter
3. **Summarizes changes** — generates a concise diff summary (via Sonnet sub-agent) so Claude knows what changed without reading the full document

On the next read, Claude sees the stale annotation and updates the affected sections automatically.

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

- **PreToolUse hook** snapshots the file before modification
- **PostToolUse sync hook** diffs, updates the link graph, detects broken links, and marks stale documents
- **PostToolUse async hook** generates change summaries in the background

### Manual (via commands)

```
/md-linker:init       # Scan all .md files and build the link graph
/md-linker:status     # Show all stale documents
/md-linker:graph      # Output a mermaid dependency graph
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

## License

MIT
