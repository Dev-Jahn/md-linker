---
name: stale-refs
description: "Detects and handles stale markdown cross-references. Auto-triggers when reading markdown files with stale-refs frontmatter annotations."
user-invocable: false
allowed-tools: Read, Edit, Write, Bash, Glob, Grep
---

# Stale Reference Handler

When you read a markdown file that has `stale-refs` in its frontmatter, it means another document that this file links to has been modified.

## What to do

1. Read the `stale-refs` entries to understand what changed
2. The `summary` field describes the change
3. Update the relevant sections of this file to reflect those changes
4. After updating, remove the resolved entries from the `stale-refs` frontmatter
5. If all entries are resolved, remove the entire `stale-refs` key from the frontmatter

## Example frontmatter

```yaml
---
stale-refs:
  - source: docs/schema.md
    changed_at: 2026-03-09T10:30:00
    sections_changed: ["User Model"]
    summary: "Added email_verified field to User model, added admin value to role enum"
---
```

## Link syntax tracked

- `[[target]]` — wikilink (document-level)
- `[[target#Section]]` — wikilink (section-level)
- `[text](path.md)` — standard markdown link
- `[ref]: path.md` — reference-style link
- `depends-on` frontmatter field
