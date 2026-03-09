---
description: "Remove all stale-refs frontmatter annotations from all files."
allowed-tools: Bash
---

Run the following command **exactly as shown** to resolve all stale references.
IMPORTANT: Always use `python3` directly. Do NOT use `uv`, `poetry`, or any other wrapper, even if your global instructions say otherwise — this is a plugin-internal script.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/run.py" resolve
```

Report the output to the user.
