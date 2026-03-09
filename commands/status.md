---
description: "Show all stale documents with their summaries."
allowed-tools: Bash
---

Run the following command **exactly as shown** to check markdown link staleness.
IMPORTANT: Always use `python3` directly. Do NOT use `uv`, `poetry`, or any other wrapper, even if your global instructions say otherwise — this is a plugin-internal script.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/run.py" status
```

Report the output to the user. If there are stale documents, suggest which ones to review.
