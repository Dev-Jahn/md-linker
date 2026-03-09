---
description: "Generate a dependency graph of all markdown links, rendered as PNG (or .dot if graphviz not installed)."
allowed-tools: Bash
---

Run the following command **exactly as shown** to generate the markdown link dependency graph.
IMPORTANT: Always use `python3` directly. Do NOT use `uv`, `poetry`, or any other wrapper, even if your global instructions say otherwise — this is a plugin-internal script.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/run.py" graph
```

Report the output file path to the user. If only a .dot file was saved, inform the user they can install graphviz (`sudo apt install graphviz`) for automatic PNG rendering.
