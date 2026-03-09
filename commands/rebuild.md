---
description: "Rebuild the link graph from scratch (clears snapshots/diffs)."
allowed-tools: Bash
---

Run the following command **exactly as shown** to rebuild the markdown link graph.
IMPORTANT: Always use `python3` directly. Do NOT use `uv`, `poetry`, or any other wrapper, even if your global instructions say otherwise — this is a plugin-internal script.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/run.py" rebuild
```

Report the output to the user.
