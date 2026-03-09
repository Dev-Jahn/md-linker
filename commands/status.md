---
description: "Show all stale documents with their summaries."
allowed-tools: Bash
---

Run the following command to check markdown link staleness:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/run.py" status
```

Report the output to the user. If there are stale documents, suggest which ones to review.
