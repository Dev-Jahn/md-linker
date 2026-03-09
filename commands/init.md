---
description: "Scan all .md files and build the link graph (.md-linker/graph.json). Run this first in a new project."
allowed-tools: Bash
---

Run the following command to initialize the markdown link graph:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/run.py" init
```

Report the output to the user.
