# Privacy Policy

**md-linker** is a local-only Claude Code plugin. It does not collect, transmit, or store any personal data.

## What this plugin does with your data

- **No data collection** — md-linker does not collect any personal information, usage analytics, or telemetry.
- **No external transmission** — All processing happens locally on your machine. No data is sent to external servers.
- **Local storage only** — The plugin stores a link graph, file snapshots, and diffs in the `.md-linker/` directory within your project. These files never leave your local filesystem.
- **Sub-agent calls** — When generating change summaries or resolving stale references, md-linker invokes the Claude CLI already present on your system. No separate API keys or accounts are required. These calls go through your existing Claude Code session.

## Third-party services

md-linker does not integrate with or send data to any third-party services.

## Contact

If you have questions about this policy, please open an issue at [github.com/Dev-Jahn/md-linker](https://github.com/Dev-Jahn/md-linker/issues).
