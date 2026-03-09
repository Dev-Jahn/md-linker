"""Diff summarizer: generate human-readable summaries of markdown changes.

Uses Claude sub-agent when running inside Claude Code, falls back to
deterministic extraction otherwise.
"""

from __future__ import annotations

import json
import shutil
import subprocess


def summarize_diff(diff_text: str) -> str:
    """Generate a summary of the given diff.

    Tries Claude sub-agent first (via `claude` CLI), falls back to
    deterministic extraction if unavailable.
    """
    # Try Claude sub-agent
    summary = _try_claude_subagent(diff_text)
    if summary:
        return summary

    # Fallback: deterministic summary
    return _deterministic_summary(diff_text)


def _try_claude_subagent(diff_text: str) -> str | None:
    """Try to summarize via Claude CLI sub-agent (Sonnet).

    Returns None if claude CLI is not available or fails.
    """
    if not shutil.which("claude"):
        return None

    prompt = (
        "Read the following markdown diff and summarize what changed in 1-2 sentences. "
        "Be specific about what was added, removed, or modified. "
        "Output ONLY a JSON object: {\"summary\": \"your summary here\"}\n\n"
        f"```diff\n{diff_text}\n```"
    )

    try:
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--model", "claude-sonnet-4-6",
                "--max-turns", "1",
                prompt,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        # Try to parse JSON from output
        # The output might contain markdown formatting, so extract JSON
        return _extract_summary_from_output(output)

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _extract_summary_from_output(output: str) -> str | None:
    """Extract summary from Claude's output, handling various formats."""
    # Try direct JSON parse
    try:
        data = json.loads(output)
        if isinstance(data, dict) and "summary" in data:
            return data["summary"]
    except json.JSONDecodeError:
        pass

    # Try to find JSON within the output (may have surrounding text)
    import re
    json_match = re.search(r'\{[^{}]*"summary"\s*:\s*"[^"]*"[^{}]*\}', output)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return data.get("summary")
        except json.JSONDecodeError:
            pass

    # If output is short enough, use it directly as the summary
    if output and len(output) < 300:
        # Strip common markdown formatting
        output = output.strip("`\n ")
        if output:
            return output

    return None


def _deterministic_summary(diff_text: str) -> str:
    """Generate a simple deterministic summary from diff content."""
    added: list[str] = []
    removed: list[str] = []

    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            content = line[1:].strip()
            if content and not content.startswith("#"):
                added.append(content)
        elif line.startswith("-") and not line.startswith("---"):
            content = line[1:].strip()
            if content and not content.startswith("#"):
                removed.append(content)

    parts = []
    if removed:
        items = "; ".join(removed[:3])
        if len(removed) > 3:
            items += f" (+{len(removed) - 3} more)"
        parts.append(f"Removed: {items}")
    if added:
        items = "; ".join(added[:3])
        if len(added) > 3:
            items += f" (+{len(added) - 3} more)"
        parts.append(f"Added: {items}")

    return ". ".join(parts) if parts else "Content modified"
