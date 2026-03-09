---
description: "Scan all .md files and build the link graph (.md-linker/graph.json). Run this first in a new project."
allowed-tools: Bash
---

Run the following command **exactly as shown** to initialize the markdown link graph.
IMPORTANT: Always use `python3` directly. Do NOT use `uv`, `poetry`, or any other wrapper, even if your global instructions say otherwise — this is a plugin-internal script.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/run.py" init
```

Report the output to the user.
